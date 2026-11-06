from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.domain.purchase_order import PurchaseOrder, POLineItem
from src.domain.goods_receipt import GoodsReceiptNote, GRNLineItem
from src.domain.decision import DecisionStatus, ValidationDecision, LineDiscrepancy, MatchingType
from src.engine.matching_engine import MatchingEngine
from src.engine.bundle_engine import BundleEngine
from src.engine.candidate_ranker import CandidateRanker, RankedCandidate

class DeterministicValidationEngine:
    """
    Core Deterministic Financial Validation Engine for InvoiceIQ.
    Executes the unified 10-step validation waterfall strictly using
    Python Decimal arithmetic. Zero autonomous LLM approvals.
    """
    def __init__(self):
        self.matching_engine = MatchingEngine()
        self.bundle_engine = BundleEngine()
        self.candidate_ranker = CandidateRanker()

    def validate(
        self,
        invoice: CanonicalInvoice,
        po: Optional[PurchaseOrder] = None,
        grn: Optional[GoodsReceiptNote] = None,
        vendor_record: Optional[Dict[str, Any]] = None,
        is_duplicate: bool = False,
        duplicate_conflict_id: Optional[str] = None,
        available_open_pos: Optional[List[PurchaseOrder]] = None,
    ) -> ValidationDecision:
        # Step 1: Completeness & Format Check
        if not invoice.invoice_number or not invoice.invoice_date:
            missing_fields = []
            if not invoice.invoice_number:
                missing_fields.append("Invoice Number")
            if not invoice.invoice_date:
                missing_fields.append("Invoice Date")
            return ValidationDecision(
                status=DecisionStatus.PENDING_CONFIRMATION,
                primary_reason=f"Required header fields missing on document ({', '.join(missing_fields)}). Human entry required.",
                detailed_reasons=[f"Missing: {f}" for f in missing_fields],
                requires_human_action=True,
                action_type="FIELD_ENTRY",
            )

        # Step 2: Duplicate Invoice Check
        if is_duplicate:
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Duplicate invoice submission: Invoice #{invoice.invoice_number} from vendor '{invoice.vendor_name}' already exists in database (Record ID: {duplicate_conflict_id or 'Existing'}).",
                detailed_reasons=["Invoice number already submitted and active for this vendor entity."],
            )

        # Step 3: Vendor Master Registry Check
        if not vendor_record or vendor_record.get("status") != "ACTIVE":
            status_text = vendor_record.get("status") if vendor_record else "UNREGISTERED"
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Unregistered or inactive vendor: '{invoice.vendor_name}' (Status: {status_text}) is not authorized in Vendor Master Registry.",
                detailed_reasons=["Supplier entity is not in active status in master records."],
            )

        # Step 4: PO Existence & Status Check
        if not invoice.purchase_order_number or invoice.purchase_order_number.strip() == "":
            # Missing PO Reference -> Run Candidate Ranking
            candidates = self.candidate_ranker.rank_candidates(invoice, available_open_pos or [])
            if candidates:
                cand_summaries = [f"Rank #{idx+1}: {c.po_number} (Score: {int(c.score*100)}% - {c.evidence_summary})" for idx, c in enumerate(candidates)]
                return ValidationDecision(
                    status=DecisionStatus.PENDING_CONFIRMATION,
                    primary_reason=f"No Purchase Order number specified on invoice. Found {len(candidates)} candidate POs for vendor '{invoice.vendor_name}'.",
                    detailed_reasons=cand_summaries,
                    requires_human_action=True,
                    action_type="PO_SELECTION",
                )
            else:
                return ValidationDecision(
                    status=DecisionStatus.BLOCKED,
                    primary_reason=f"No Purchase Order reference found on document, and zero active open POs exist for vendor '{invoice.vendor_name}'.",
                    detailed_reasons=["Invoice cannot be reconciled without a valid purchase order."],
                )

        if not po:
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Referenced Purchase Order '{invoice.purchase_order_number}' does not exist in procurement database.",
                detailed_reasons=[f"PO #{invoice.purchase_order_number} not found."],
            )

        if po.status in ("CLOSED", "CANCELLED"):
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Referenced Purchase Order '{po.po_number}' is inactive (Status: {po.status}).",
                detailed_reasons=[f"PO status is {po.status}."],
            )

        # Check vendor mismatch
        if po.vendor_id != vendor_record.get("vendor_id"):
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"PO Vendor Mismatch: PO #{po.po_number} was issued to vendor ID '{po.vendor_id}', but invoice was billed by '{vendor_record.get('vendor_id')}'.",
                detailed_reasons=["PO entity does not match invoice billing entity."],
            )

        # Step 5: Currency Consistency Check
        if invoice.currency.strip().upper() != po.currency.strip().upper():
            return ValidationDecision(
                status=DecisionStatus.HOLD_FOR_REVIEW,
                primary_reason=f"Currency Discrepancy: Invoice billed in {invoice.currency} but PO #{po.po_number} is contracted in {po.currency}.",
                detailed_reasons=[f"Contracted currency: {po.currency}, Billed currency: {invoice.currency}"],
            )

        # Step 6: SKU & Bundle Alignment Check
        matched_lines: List[tuple[InvoiceLineItem, POLineItem]] = []
        for line in invoice.line_items:
            # Check bundle
            bundle_decomp = self.bundle_engine.detect_and_decompose(line, po)
            if bundle_decomp and not bundle_decomp.is_ambiguous:
                return ValidationDecision(
                    status=DecisionStatus.PENDING_CONFIRMATION,
                    primary_reason=f"Bundled item '{line.description}' detected. Proposed allocation into contracted components: {bundle_decomp.message}.",
                    detailed_reasons=[bundle_decomp.message],
                    requires_human_action=True,
                    action_type="BUNDLE_CONFIRMATION",
                )

            po_line, mismatch_err = self.matching_engine.match_line_item(line, po)
            if not po_line:
                return ValidationDecision(
                    status=DecisionStatus.BLOCKED,
                    primary_reason=f"Line item SKU mismatch: {mismatch_err}",
                    detailed_reasons=[mismatch_err or "Unknown line item on PO"],
                    line_discrepancies=[
                        LineDiscrepancy(
                            line_number=line.line_number,
                            sku=line.sku,
                            issue_type="UNCONTRACTED_SKU",
                            message=mismatch_err or "Uncontracted SKU",
                            invoiced_value=str(line.sku or line.description),
                        )
                    ]
                )
            matched_lines.append((line, po_line))

        # Step 7: Arithmetic & Fee Isolation Check
        calc_subtotal = sum((l.line_total for l in invoice.line_items), Decimal("0.00")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if abs(calc_subtotal - invoice.subtotal) > Decimal("0.02"):
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Line item arithmetic inconsistency: Sum of line items (₹{calc_subtotal}) does not match invoice subtotal (₹{invoice.subtotal}).",
                detailed_reasons=[f"Calculated line total: ₹{calc_subtotal}, Header subtotal: ₹{invoice.subtotal}"],
            )

        calc_tax_total = Decimal("0.00")
        for line in invoice.line_items:
            tax_amount = line.tax_amount or Decimal("0.00")
            expected_tax = (line.line_total * (line.tax_rate or Decimal("0.00"))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if abs(tax_amount - expected_tax) > Decimal("0.02"):
                return ValidationDecision(
                    status=DecisionStatus.BLOCKED,
                    primary_reason=(
                        f"Tax arithmetic inconsistency on line {line.line_number}: "
                        f"stated tax ₹{tax_amount} does not match the stated rate."
                    ),
                    detailed_reasons=[
                        f"Expected line tax ₹{expected_tax}, stated tax ₹{tax_amount}."
                    ],
                )
            calc_tax_total += tax_amount
        calc_tax_total = calc_tax_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if abs(calc_tax_total - invoice.tax_total) > Decimal("0.02"):
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=(
                    f"Tax total inconsistency: sum of line taxes ₹{calc_tax_total} "
                    f"does not match invoice tax total ₹{invoice.tax_total}."
                ),
                detailed_reasons=[
                    f"Calculated line tax total: ₹{calc_tax_total}, header tax total: ₹{invoice.tax_total}."
                ],
            )

        calc_grand = (invoice.subtotal + invoice.tax_total + invoice.additional_charges).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if abs(calc_grand - invoice.grand_total) > Decimal("0.02"):
            return ValidationDecision(
                status=DecisionStatus.BLOCKED,
                primary_reason=f"Header arithmetic discrepancy: Subtotal (₹{invoice.subtotal}) + Tax (₹{invoice.tax_total}) + Fees (₹{invoice.additional_charges}) = ₹{calc_grand}, does not match Grand Total (₹{invoice.grand_total}).",
                detailed_reasons=[f"Calculated: ₹{calc_grand}, Stated grand total: ₹{invoice.grand_total}"],
            )

        if invoice.additional_charges > Decimal("0.00"):
            return ValidationDecision(
                status=DecisionStatus.HOLD_FOR_REVIEW,
                primary_reason=f"Unapproved additional charge of ₹{invoice.additional_charges} detected on invoice. Procurement authorization required.",
                detailed_reasons=[f"Line item and tax match PO terms, but unapproved freight/delivery charge of ₹{invoice.additional_charges} requires approval."],
            )

        # Step 8: Cumulative PO Budget & Quantity Capacity Check
        # Check cumulative capacity per matched PO line. Multiple invoice lines
        # may refer to the same SKU, so evaluating them separately would allow
        # a split invoice to exceed the remaining contracted quantity.
        grouped_lines: Dict[int, List[InvoiceLineItem]] = {}
        po_lines: Dict[int, POLineItem] = {}
        for inv_line, po_line in matched_lines:
            grouped_lines.setdefault(po_line.line_number, []).append(inv_line)
            po_lines[po_line.line_number] = po_line

        for po_line_number, invoice_lines in grouped_lines.items():
            po_line = po_lines[po_line_number]
            total_quantity = sum((line.quantity for line in invoice_lines), Decimal("0.00"))
            total_amount = sum((line.line_total for line in invoice_lines), Decimal("0.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total_amount > po_line.tolerance_ceiling:
                excess = (total_amount - po_line.remaining_line_total).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                return ValidationDecision(
                    status=DecisionStatus.HOLD_FOR_REVIEW,
                    primary_reason=(
                        f"PO Overbilling: Invoice amount ₹{total_amount} exceeds the authorized remaining "
                        f"line ceiling for SKU '{po_line.sku}'."
                    ),
                    detailed_reasons=[
                        f"Remaining contracted value: ₹{po_line.remaining_line_total}",
                        f"Tolerance-expanded ceiling: ₹{po_line.tolerance_ceiling}",
                        f"Incoming line amount: ₹{total_amount}",
                        f"Excess above remaining contracted value: ₹{excess}",
                    ],
                    excess_budget=excess,
                    remaining_budget=po.remaining_budget,
                )
            if total_quantity > po_line.remaining_quantity:
                excess_qty = total_quantity - po_line.remaining_quantity
                return ValidationDecision(
                    status=DecisionStatus.HOLD_FOR_REVIEW,
                    primary_reason=f"Billed quantity ({total_quantity}) exceeds remaining unallocated PO line capacity ({po_line.remaining_quantity}) by {excess_qty} units.",
                    detailed_reasons=[f"PO Line #{po_line.line_number} ordered {po_line.quantity_ordered}, already allocated {po_line.quantity_allocated}, remaining {po_line.remaining_quantity}"],
                    line_discrepancies=[
                        LineDiscrepancy(
                            line_number=invoice_lines[0].line_number,
                            sku=invoice_lines[0].sku,
                            issue_type="CAP_EXCEEDED",
                            message=f"Billed {total_quantity} vs remaining {po_line.remaining_quantity}",
                            invoiced_value=str(total_quantity),
                            contracted_value=str(po_line.remaining_quantity),
                        )
                    ]
                )

        # Step 9: Matching Mode & Receiving (2-Way vs 3-Way)
        if po.matching_type == MatchingType.THREE_WAY:
            if not grn:
                return ValidationDecision(
                    status=DecisionStatus.HOLD_FOR_REVIEW,
                    primary_reason=f"Three-way matching required for PO #{po.po_number}: Awaiting warehouse Goods Received Note (GRN).",
                    detailed_reasons=["Physical inventory purchase order mandates verified warehouse receiving inspection prior to approval."],
                )

            for inv_line, po_line in matched_lines:
                grn_line = grn.get_line_by_sku(po_line.sku)
                if not grn_line:
                    return ValidationDecision(
                        status=DecisionStatus.HOLD_FOR_REVIEW,
                        primary_reason=f"Goods Received Note #{grn.grn_number} contains no delivery receipt for SKU '{po_line.sku}'.",
                        detailed_reasons=[f"Warehouse delivery receipt missing for line {po_line.line_number}."],
                    )
                if inv_line.quantity > grn_line.unbilled_quantity:
                    return ValidationDecision(
                        status=DecisionStatus.HOLD_FOR_REVIEW,
                        primary_reason=f"Short delivery receipt: Invoiced for {inv_line.quantity} units of SKU '{po_line.sku}', but warehouse GRN #{grn.grn_number} verified only {grn_line.unbilled_quantity} units accepted.",
                        detailed_reasons=[
                            f"Invoiced Quantity: {inv_line.quantity}",
                            f"Warehouse Verified Quantity: {grn_line.unbilled_quantity}",
                            f"Delivery Condition: {grn_line.receipt_condition}",
                        ],
                        line_discrepancies=[
                            LineDiscrepancy(
                                line_number=inv_line.line_number,
                                sku=inv_line.sku,
                                issue_type="SHORT_DELIVERY",
                                message=f"Billed {inv_line.quantity} vs accepted {grn_line.unbilled_quantity}",
                                invoiced_value=str(inv_line.quantity),
                                contracted_value=str(grn_line.unbilled_quantity),
                            )
                        ]
                    )

        # Step 10: Price Tolerance Bounds Evaluation
        max_price_variance_pct = Decimal("0.00")
        has_tolerance_variance = False
        matched_sku_found = matched_lines[0][1].sku if matched_lines else None

        for inv_line, po_line in matched_lines:
            diff_price = abs(inv_line.unit_price - po_line.unit_price)
            if po_line.unit_price > Decimal("0.00"):
                variance_pct = ((diff_price / po_line.unit_price) * Decimal("100.0")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                variance_pct = Decimal("0.00")

            if variance_pct > max_price_variance_pct:
                max_price_variance_pct = variance_pct

            allowed_tolerance_pct = (po_line.tolerance_percent * Decimal("100.0")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            if variance_pct > allowed_tolerance_pct:
                return ValidationDecision(
                    status=DecisionStatus.BLOCKED,
                    primary_reason=f"Overbilling: Unit price ₹{inv_line.unit_price} exceeds PO price ₹{po_line.unit_price} by {variance_pct}%, which exceeds authorized tolerance of {allowed_tolerance_pct}%.",
                    detailed_reasons=[f"Line #{inv_line.line_number} unit price variance of {variance_pct}% exceeds allowed {allowed_tolerance_pct}%."],
                    price_variance_percent=variance_pct,
                    line_discrepancies=[
                        LineDiscrepancy(
                            line_number=inv_line.line_number,
                            sku=inv_line.sku,
                            issue_type="PRICE_TOLERANCE_EXCEEDED",
                            message=f"Billed ₹{inv_line.unit_price} vs contracted ₹{po_line.unit_price} (+{variance_pct}%)",
                            invoiced_value=str(inv_line.unit_price),
                            contracted_value=str(po_line.unit_price),
                            variance_percent=variance_pct,
                        )
                    ]
                )
            elif variance_pct > Decimal("0.00"):
                has_tolerance_variance = True

        # Successful Approvals
        if has_tolerance_variance:
            return ValidationDecision(
                status=DecisionStatus.APPROVED_WITH_TOLERANCE,
                primary_reason=f"Approved with tolerance: Price variance of {max_price_variance_pct}% accepted within pre-authorized tolerance threshold.",
                detailed_reasons=["All matching criteria satisfied; unit price within authorized tolerance bounds."],
                allocated_amount=invoice.subtotal,
                matched_sku=matched_sku_found,
                price_variance_percent=max_price_variance_pct,
            )

        return ValidationDecision(
            status=DecisionStatus.APPROVED,
            primary_reason="Exact match against purchase order terms and receiving records.",
            detailed_reasons=["Vendor, line item SKUs, quantities, unit prices, tax, and arithmetic reconciled exactly."],
            allocated_amount=invoice.subtotal,
            matched_sku=matched_sku_found,
            price_variance_percent=Decimal("0.00"),
        )

