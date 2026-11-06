import uuid
import hashlib
import asyncio
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import date, datetime

from src.domain.invoice import CanonicalInvoice, InvoiceLineItem
from src.domain.decision import DecisionStatus, ValidationDecision, MatchingType
from src.domain.purchase_order import PurchaseOrder
from src.domain.goods_receipt import GoodsReceiptNote
from src.storage.connection import get_connection
from src.storage.transaction import transaction
from src.storage.repositories.vendor_repository import VendorRepository
from src.storage.repositories.po_repository import PORepository
from src.storage.repositories.grn_repository import GRNRepository
from src.storage.repositories.invoice_repository import InvoiceRepository
from src.storage.repositories.audit_repository import AuditRepository
from src.storage.repositories.document_repository import DocumentRepository
from src.extraction.document_parser import DocumentParser, ParsedDocument
from src.extraction.router import ProviderRouter
from src.engine.validation_engine import DeterministicValidationEngine
from src.engine.candidate_ranker import RankedCandidate

class InvoiceProcessingService:
    """
    Application Service Facade orchestrating Document Intelligence, AI Extraction,
    Deterministic Validation, Human Revalidation, and Transactional SQLite Storage.
    """
    def __init__(
        self,
        db_path: str,
        router: Optional[ProviderRouter] = None,
        parser: Optional[DocumentParser] = None,
    ):
        self.db_path = db_path
        self.parser = parser or DocumentParser()
        self.engine = DeterministicValidationEngine()
        self.router = router  # If None, instantiated with connection-backed audit repo

    def _get_repos(self, conn):
        return (
            VendorRepository(conn),
            PORepository(conn),
            GRNRepository(conn),
            InvoiceRepository(conn),
            AuditRepository(conn),
        )

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        with get_connection(self.db_path) as conn:
            return InvoiceRepository(conn).get_dashboard_metrics()

    def list_invoices(self, limit: int = 20) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            return InvoiceRepository(conn).list_invoices(limit=limit)

    def list_recent_audit_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            return AuditRepository(conn).list_recent(limit=limit)

    def rank_po_candidates(self, invoice_id: str) -> List[RankedCandidate]:
        with get_connection(self.db_path) as conn:
            inv_record = InvoiceRepository(conn).get_by_id(invoice_id)
            if not inv_record:
                raise ValueError(f"Invoice {invoice_id} not found.")
            vendor = VendorRepository(conn).find_by_name_or_tax_id(inv_record["vendor_name"])
            open_pos = PORepository(conn).find_by_vendor_id(vendor["vendor_id"]) if vendor else []
        invoice_date = inv_record["invoice_date"]
        if isinstance(invoice_date, str):
            invoice_date = datetime.strptime(invoice_date[:10], "%Y-%m-%d").date()
        lines = [
            InvoiceLineItem(
                line_number=line["line_number"],
                sku=line.get("sku"),
                description=line["description"],
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line["unit_price"])),
                line_total=Decimal(str(line["line_total"])),
                tax_rate=Decimal(str(line.get("tax_rate") or "0.00")),
                tax_amount=Decimal(str(line.get("tax_amount") or "0.00")),
            )
            for line in inv_record["line_items"]
        ]
        invoice = CanonicalInvoice(
            invoice_number=inv_record["invoice_number"],
            vendor_name=inv_record["vendor_name"],
            invoice_date=invoice_date,
            currency=inv_record["currency"],
            subtotal=Decimal(str(inv_record["subtotal"])),
            tax_total=Decimal(str(inv_record["tax_total"])),
            additional_charges=Decimal(str(inv_record["additional_charges"])),
            grand_total=Decimal(str(inv_record["grand_total"])),
            line_items=lines,
            raw_document_hash=inv_record["raw_document_hash"],
            extraction_provider=inv_record["extraction_provider"],
        )
        return self.engine.candidate_ranker.rank_candidates(invoice, open_pos)

    @staticmethod
    def _invoice_from_record(inv_record: Dict[str, Any]) -> CanonicalInvoice:
        invoice_date = inv_record["invoice_date"]
        if isinstance(invoice_date, str):
            invoice_date = datetime.strptime(invoice_date[:10], "%Y-%m-%d").date()
        lines = [
            InvoiceLineItem(
                line_number=line["line_number"],
                sku=line.get("sku"),
                description=line["description"],
                quantity=Decimal(str(line["quantity"])),
                unit_price=Decimal(str(line["unit_price"])),
                line_total=Decimal(str(line["line_total"])),
                tax_amount=Decimal(str(line.get("tax_amount") or "0.00")),
            )
            for line in inv_record["line_items"]
        ]
        return CanonicalInvoice(
            invoice_number=inv_record["invoice_number"],
            vendor_name=inv_record["vendor_name"],
            invoice_date=invoice_date,
            purchase_order_number=inv_record["po_number"],
            currency=inv_record["currency"],
            subtotal=Decimal(str(inv_record["subtotal"])),
            tax_total=Decimal(str(inv_record["tax_total"])),
            additional_charges=Decimal(str(inv_record["additional_charges"])),
            grand_total=Decimal(str(inv_record["grand_total"])),
            line_items=lines,
            raw_document_hash=inv_record["raw_document_hash"],
            extraction_provider=inv_record["extraction_provider"],
        )

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        with get_connection(self.db_path) as conn:
            return InvoiceRepository(conn).get_by_id(invoice_id)

    def revalidate_invoice(
        self,
        invoice_id: str,
        corrected_invoice: CanonicalInvoice,
        actor: str = "USER:ap_officer",
    ) -> Dict[str, Any]:
        """Audit a human correction and rerun the complete deterministic waterfall."""
        with get_connection(self.db_path) as conn:
            inv_repo = InvoiceRepository(conn)
            audit_repo = AuditRepository(conn)
            existing = inv_repo.get_by_id(invoice_id)
            if not existing:
                raise ValueError(f"Invoice {invoice_id} not found.")
            if existing["status"] in (
                DecisionStatus.APPROVED.value,
                DecisionStatus.APPROVED_WITH_TOLERANCE.value,
            ):
                raise ValueError("Approved invoices cannot be altered through correction workflow.")
            original = self._invoice_from_record(existing)
            corrected_invoice = corrected_invoice.model_copy(
                update={
                    "raw_document_hash": original.raw_document_hash,
                    "extraction_provider": original.extraction_provider,
                }
            )
            before = original.model_dump(mode="json")
            after = corrected_invoice.model_dump(mode="json")
            if before == after:
                raise ValueError("No correction was supplied for revalidation.")
            audit_repo.append_event(
                entity_type="INVOICE",
                entity_id=invoice_id,
                event_type="HUMAN_CORRECTION",
                actor=actor,
                payload={"before": before, "after": after},
            )
        return self._execute_validation_and_storage(
            corrected_invoice,
            b"",
            existing_invoice_id=invoice_id,
        )

    def process_invoice_document(
        self,
        file_bytes: bytes,
        filename: str = "invoice.pdf",
        provided_invoice: Optional[CanonicalInvoice] = None,
    ) -> Dict[str, Any]:
        doc_hash = hashlib.sha256(file_bytes).hexdigest()

        with get_connection(self.db_path) as conn:
            vendor_repo, po_repo, grn_repo, inv_repo, audit_repo = self._get_repos(conn)

            # Check Identical Document Replay (Case A of E_DUP)
            existing_by_hash = inv_repo.find_by_hash(doc_hash)
            if existing_by_hash:
                audit_repo.append_event(
                    entity_type="INVOICE",
                    entity_id=existing_by_hash["invoice_id"],
                    event_type="DOCUMENT_REPLAY",
                    actor="SYSTEM",
                    payload={"hash": doc_hash, "invoice_id": existing_by_hash["invoice_id"]}
                )
                return {
                    "invoice_id": existing_by_hash["invoice_id"],
                    "is_replay": True,
                    "status": existing_by_hash["status"],
                    "decision_reason": f"Identical Document Replay: This exact file was previously processed as Invoice #{existing_by_hash['invoice_number']}. Showing existing record.",
                    "allocated_amount": Decimal("0.00"),
                    "invoice_record": existing_by_hash,
                }

        # A canonical invoice is an explicit injection point used by integrations
        # and tests. Otherwise, always process the uploaded document itself.
        if provided_invoice:
            canonical_inv = provided_invoice
            raw_bytes = file_bytes
        else:
            parsed_doc = self.parser.parse(file_bytes, filename)
            with get_connection(self.db_path) as conn:
                DocumentRepository(conn).store_source(
                    document_hash=parsed_doc.sha256_hash,
                    filename=filename,
                    mime_type="application/pdf",
                    document_bytes=parsed_doc.raw_bytes,
                    extracted_text=parsed_doc.text_content,
                    page_count=parsed_doc.page_count,
                    is_scanned=parsed_doc.is_scanned,
                )
            canonical_inv = self._extract_canonical(parsed_doc)
            raw_bytes = parsed_doc.raw_bytes

        # The uploaded artifact is the authoritative idempotency identity.
        canonical_inv = canonical_inv.model_copy(update={"raw_document_hash": doc_hash})

        # Step C: Reconcile and Validate
        return self._execute_validation_and_storage(canonical_inv, raw_bytes)

    def _extract_canonical(self, parsed_doc: ParsedDocument) -> CanonicalInvoice:
        """Extract invoice fields through the configured provider contract."""
        with get_connection(self.db_path) as conn:
            audit_repo = AuditRepository(conn)
            router = self.router or ProviderRouter(audit_repo=audit_repo)
            result = asyncio.run(
                router.extract(
                    document_bytes=parsed_doc.raw_bytes,
                    mime_type="application/pdf",
                    extracted_text=parsed_doc.text_content,
                    page_images_b64=parsed_doc.page_images_b64,
                    raw_document_hash=parsed_doc.sha256_hash,
                )
            )
            DocumentRepository(conn).record_extraction(
                document_hash=parsed_doc.sha256_hash,
                provider_name=result.provider_name,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                raw_response_text=result.raw_response_text,
            )
            audit_repo.append_event(
                entity_type="DOCUMENT",
                entity_id=parsed_doc.sha256_hash,
                event_type="AI_EXTRACTION_COMPLETED",
                actor=result.provider_name.upper(),
                payload={
                    "provider": result.provider_name,
                    "latency_ms": result.latency_ms,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "raw_response": result.raw_response_text,
                },
            )
            return result.invoice

    def _execute_validation_and_storage(
        self,
        invoice: CanonicalInvoice,
        raw_bytes: bytes,
        existing_invoice_id: Optional[str] = None
    ) -> Dict[str, Any]:
        invoice_id = existing_invoice_id or str(uuid.uuid4())

        with get_connection(self.db_path) as conn:
            vendor_repo, po_repo, grn_repo, inv_repo, audit_repo = self._get_repos(conn)

            # Match Vendor
            vendor_record = vendor_repo.find_by_name_or_tax_id(invoice.vendor_name, invoice.vendor_tax_id)
            vendor_id = vendor_record["vendor_id"] if vendor_record else None

            # Check Duplicate Invoice Number with different hash (Case B of E_DUP)
            is_dup = False
            conflict_id = None
            if vendor_id and invoice.invoice_number:
                dup_record = inv_repo.find_active_duplicate(vendor_id, invoice.invoice_number, exclude_id=invoice_id)
                if dup_record and dup_record["raw_document_hash"] != invoice.raw_document_hash:
                    is_dup = True
                    conflict_id = dup_record["invoice_id"]

            # Load PO and GRN
            po = None
            open_pos = []
            if invoice.purchase_order_number:
                po = po_repo.get_by_number(invoice.purchase_order_number)
            elif vendor_id:
                open_pos = po_repo.find_by_vendor_id(vendor_id, status="ACTIVE")

            grn = None
            if po and po.matching_type == MatchingType.THREE_WAY:
                grn = grn_repo.get_by_po_number(po.po_number)

            # Run 10-step Deterministic Validation Waterfall
            decision = self.engine.validate(
                invoice=invoice,
                po=po,
                grn=grn,
                vendor_record=vendor_record,
                is_duplicate=is_dup,
                duplicate_conflict_id=conflict_id,
                available_open_pos=open_pos,
            )
            decision.invoice_id = invoice_id

            # Atomic Commit if Approved
            with transaction(conn):
                # Re-read balances and duplicate state after BEGIN IMMEDIATE.
                # This serializes competing approvals so two invoices cannot
                # both validate against the same stale PO/GRN capacity.
                vendor_record = vendor_repo.find_by_name_or_tax_id(invoice.vendor_name, invoice.vendor_tax_id)
                vendor_id = vendor_record["vendor_id"] if vendor_record else None
                if po:
                    po = po_repo.get_by_number(po.po_number)
                    grn = grn_repo.get_by_po_number(po.po_number) if po and po.matching_type == MatchingType.THREE_WAY else None
                duplicate_now = (
                    inv_repo.find_active_duplicate(vendor_id, invoice.invoice_number, exclude_id=invoice_id)
                    if vendor_id and invoice.invoice_number
                    else None
                )
                is_duplicate_now = bool(
                    duplicate_now and duplicate_now["raw_document_hash"] != invoice.raw_document_hash
                )
                decision = self.engine.validate(
                    invoice=invoice,
                    po=po,
                    grn=grn,
                    vendor_record=vendor_record,
                    is_duplicate=is_duplicate_now,
                    duplicate_conflict_id=duplicate_now["invoice_id"] if is_duplicate_now else None,
                    available_open_pos=open_pos,
                )
                decision.invoice_id = invoice_id
                inv_repo.insert_invoice(
                    invoice_id=invoice_id,
                    invoice=invoice,
                    status=decision.status,
                    decision_reason=decision.primary_reason,
                    vendor_id=vendor_id,
                    persist_po_number=po.po_number if po else None,
                )

                if decision.status in (DecisionStatus.APPROVED, DecisionStatus.APPROVED_WITH_TOLERANCE) and po:
                    # Allocate PO balances
                    for inv_line in invoice.line_items:
                        po_line = po.get_line_by_sku(inv_line.sku or "")
                        if not po_line and len(po.line_items) == 1:
                            po_line = po.line_items[0]
                        if po_line:
                            inv_repo.record_allocation(
                                po_number=po.po_number,
                                po_line_number=po_line.line_number,
                                invoice_id=invoice_id,
                                invoice_line_number=inv_line.line_number,
                                quantity_allocated=inv_line.quantity,
                                amount_allocated=inv_line.line_total,
                            )
                            po_repo.increment_allocation(
                                po_number=po.po_number,
                                line_number=po_line.line_number,
                                qty_to_add=inv_line.quantity,
                            )

                    audit_repo.append_event(
                        entity_type="INVOICE",
                        entity_id=invoice_id,
                        event_type="VALIDATION_APPROVED",
                        actor="SYSTEM",
                        payload={
                            "status": decision.status.value,
                            "allocated_amount": str(decision.allocated_amount),
                            "po_number": po.po_number,
                        }
                    )
                else:
                    audit_repo.append_event(
                        entity_type="INVOICE",
                        entity_id=invoice_id,
                        event_type="VALIDATION_EVALUATED",
                        actor="SYSTEM",
                        payload={
                            "status": decision.status.value,
                            "reason": decision.primary_reason,
                        }
                    )

            # Re-fetch invoice record for complete return payload
            saved_inv = inv_repo.get_by_id(invoice_id)
            return {
                "invoice_id": invoice_id,
                "is_replay": False,
                "status": decision.status.value,
                "primary_reason": decision.primary_reason,
                "detailed_reasons": decision.detailed_reasons,
                "allocated_amount": decision.allocated_amount,
                "excess_budget": decision.excess_budget,
                "remaining_budget": decision.remaining_budget,
                "matched_sku": decision.matched_sku,
                "price_variance_percent": decision.price_variance_percent,
                "requires_human_action": decision.requires_human_action,
                "action_type": decision.action_type,
                "invoice_record": saved_inv,
                "decision": decision,
            }

    def confirm_po_selection(self, invoice_id: str, selected_po_number: str) -> Dict[str, Any]:
        """Human action: confirm PO candidate selection and trigger complete revalidation."""
        with get_connection(self.db_path) as conn:
            inv_repo = InvoiceRepository(conn)
            audit_repo = AuditRepository(conn)
            inv_record = inv_repo.get_by_id(invoice_id)
            if not inv_record:
                raise ValueError(f"Invoice {invoice_id} not found.")
            if inv_record["status"] != DecisionStatus.PENDING_CONFIRMATION.value:
                raise ValueError("PO selection is only allowed for invoices pending confirmation.")

            audit_repo.append_event(
                entity_type="INVOICE",
                entity_id=invoice_id,
                event_type="HUMAN_CONFIRMATION",
                actor="USER:ap_officer",
                payload={"action": "SELECT_PO", "selected_po_number": selected_po_number}
            )

        # Re-construct working CanonicalInvoice
        lines = [
            InvoiceLineItem(
                line_number=l["line_number"],
                sku=l.get("sku"),
                description=l["description"],
                quantity=Decimal(str(l["quantity"])),
                unit_price=Decimal(str(l["unit_price"])),
                line_total=Decimal(str(l["line_total"])),
                tax_rate=Decimal(str(l.get("tax_rate") or "0.00")),
                tax_amount=Decimal(str(l.get("tax_amount") or "0.00")),
            )
            for l in inv_record["line_items"]
        ]
        dt = inv_record["invoice_date"]
        inv_dt = datetime.strptime(dt[:10], "%Y-%m-%d").date() if isinstance(dt, str) else dt

        updated_inv = CanonicalInvoice(
            invoice_number=inv_record["invoice_number"],
            vendor_name=inv_record["vendor_name"],
            invoice_date=inv_dt,
            purchase_order_number=selected_po_number,
            currency=inv_record["currency"],
            subtotal=Decimal(str(inv_record["subtotal"])),
            tax_total=Decimal(str(inv_record["tax_total"])),
            additional_charges=Decimal(str(inv_record["additional_charges"])),
            grand_total=Decimal(str(inv_record["grand_total"])),
            line_items=lines,
            raw_document_hash=inv_record["raw_document_hash"],
            extraction_provider=inv_record["extraction_provider"],
            extraction_confidence=Decimal("1.00"),
        )
        return self._execute_validation_and_storage(updated_inv, b"", existing_invoice_id=invoice_id)

    def confirm_bundle_decomposition(self, invoice_id: str) -> Dict[str, Any]:
        """Human action: accept bundle decomposition and trigger complete revalidation."""
        with get_connection(self.db_path) as conn:
            inv_repo = InvoiceRepository(conn)
            po_repo = PORepository(conn)
            audit_repo = AuditRepository(conn)
            inv_record = inv_repo.get_by_id(invoice_id)
            if not inv_record:
                raise ValueError(f"Invoice {invoice_id} not found.")
            if inv_record["status"] != DecisionStatus.PENDING_CONFIRMATION.value:
                raise ValueError("Bundle confirmation is only allowed for invoices pending confirmation.")

            po = po_repo.get_by_number(inv_record["po_number"])
            if not po:
                raise ValueError(f"PO {inv_record['po_number']} not found.")

            original = self._invoice_from_record(inv_record)
            decomposition = None
            for line in original.line_items:
                candidate = self.engine.bundle_engine.detect_and_decompose(line, po)
                if candidate and not candidate.is_ambiguous:
                    decomposition = candidate
                    break
            if not decomposition:
                raise ValueError("No unambiguous bundle decomposition is available for this invoice.")

            audit_repo.append_event(
                entity_type="INVOICE",
                entity_id=invoice_id,
                event_type="HUMAN_CONFIRMATION",
                actor="USER:ap_officer",
                payload={"action": "CONFIRM_BUNDLE_DECOMPOSITION"}
            )
        subtotal = sum((line.line_total for line in decomposition.decomposed_lines), Decimal("0.00"))
        tax_total = sum((line.tax_amount or Decimal("0.00") for line in decomposition.decomposed_lines), Decimal("0.00"))
        updated_inv = original.model_copy(
            update={
                "line_items": decomposition.decomposed_lines,
                "subtotal": subtotal,
                "tax_total": tax_total,
                "grand_total": subtotal + tax_total + original.additional_charges,
            }
        )
        return self.revalidate_invoice(invoice_id, updated_inv)

