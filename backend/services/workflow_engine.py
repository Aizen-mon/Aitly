"""Rule-based business workflow engine for voice and chat assistants."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from database import session_scope
from models import Customer, Invoice, Payment, Product, Transaction
from services.entity_parser import EntityParser
from services.response_builder import ResponseBuilder


class WorkflowEngine:
    def __init__(self, repos, invoice_service, dashboard_service, tally_service=None):
        self.repos = repos
        self.invoice_service = invoice_service
        self.dashboard = dashboard_service
        self.tally = tally_service
        self.parser = EntityParser()
        self.builder = ResponseBuilder()

    def _ensure_session(self, session_id: str):
        state = self.repos.conversation_sessions.get_by_session(session_id)
        if state:
            return state
        return self.repos.conversation_sessions.create(
            session_id=session_id,
            current_flow=None,
            current_step=None,
            context_json=json.dumps({}),
        )

    def _context(self, state) -> Dict[str, Any]:
        try:
            return json.loads(state.context_json or "{}")
        except Exception:
            return {}

    def _save(self, state, context: Dict[str, Any], flow: Optional[str], step: Optional[str]):
        return self.repos.conversation_sessions.update(
            state,
            context_json=json.dumps(context),
            current_flow=flow,
            current_step=step,
        )

    def process(
        self,
        *,
        session_id: str,
        text: str,
        parsed: Dict[str, Any],
        product_names: Optional[Iterable[str]] = None,
        customer_names: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        session_state = self._ensure_session(session_id)
        context = self._context(session_state)
        entities = dict(parsed.get("entities", {}) or {})
        intent = parsed.get("intent") or self.parser.infer_intent(text)
        normalized = text.strip().lower()
        product_names = list(product_names or [])
        customer_names = list(customer_names or [])

        entities.update(self.parser.extract(text, product_names=product_names, customer_names=customer_names, context=context))

        if session_state.current_flow == "create_invoice":
            return self._continue_invoice_flow(session_state, context, text, entities, product_names, customer_names)
        if session_state.current_flow == "record_payment":
            return self._continue_payment_flow(session_state, context, text, entities)
        if session_state.current_flow == "inventory_action":
            return self._continue_inventory_flow(session_state, context, text, entities)

        if intent == "create_invoice":
            return self._start_invoice_flow(session_state, context, entities)
        if intent == "record_payment":
            return self._start_payment_flow(session_state, context, entities)
        if intent in {"add_inventory", "update_inventory", "delete_inventory", "search_inventory", "low_stock", "inventory_summary"}:
            return self._handle_inventory_intent(intent, session_state, context, text, entities)
        if intent in {"today_sales", "pending_dues", "overdue_customers", "recent_transactions", "top_products", "sales_summary"}:
            return self._handle_business_intent(intent, session_state, entities)

        if "dashboard" in normalized or "refresh" in normalized:
            return self.builder.build(
                intent="dashboard_summary",
                title="Dashboard refreshed",
                message="Dashboard data is refreshed and ready.",
                action="view_dashboard",
                details=self.dashboard.get_quotation_context(),
                session_state={"flow": None, "step": None},
            )

        context["last_text"] = text
        self._save(session_state, context, None, None)
        return self.builder.build(
            intent="general",
            title="How can I help?",
            message="I can help with invoices, payments, inventory, dues, sales, and dashboard updates.",
            action="show_suggestions",
            suggestions=[
                "Create invoice",
                "Record payment",
                "Show low stock items",
                "Show pending dues",
            ],
            session_state={"flow": None, "step": None},
        )

    def _start_invoice_flow(self, state, context, entities: Dict[str, Any]):
        draft = context.setdefault("draft_invoice", {"items": []})
        customer_name = entities.get("customer_name")
        items = entities.get("items") or []
        if customer_name:
            draft["customer_name"] = customer_name
        if items:
            draft["items"] = items

        if not customer_name:
            self._save(state, context, "create_invoice", "customer_name")
            return self.builder.prompt(
                "Create Invoice",
                "What is the customer name?",
                "customer_name",
                "create_invoice",
                details={"draft_invoice": draft},
            )

        if not items:
            self._save(state, context, "create_invoice", "items")
            return self.builder.prompt("Create Invoice", f"Customer '{customer_name}' noted. What items should I add?", "items", "create_invoice")

        total = self._estimate_invoice_total(items)
        draft["total"] = total
        draft["customer_name"] = customer_name
        self._save(state, context, "create_invoice", "confirm")
        return self.builder.build(
            intent="create_invoice",
            title="Confirm Invoice",
            message=f"Invoice total is ₹{total:,.0f}. Confirm?",
            action="confirm_invoice",
            details={"draft_invoice": draft, "total": total},
            session_state={"flow": "create_invoice", "step": "confirm"},
            speech=f"Invoice total is rupees {total:,.0f}. Confirm?",
        )

    def _continue_invoice_flow(self, state, context, text: str, entities: Dict[str, Any], product_names: List[str], customer_names: List[str]):
        draft = context.setdefault("draft_invoice", {"items": []})
        step = state.current_step or "customer_name"
        if step == "customer_name":
            customer_name = entities.get("customer_name") or self.parser.extract(text, customer_names=customer_names).get("customer_name") or text.strip()
            draft["customer_name"] = customer_name
            self._save(state, context, "create_invoice", "items")
            return self.builder.prompt("Create Invoice", f"Customer '{customer_name}' noted. What items should I add?", "items", "create_invoice")

        if step == "items":
            items = entities.get("items") or self.parser.extract(text, product_names=product_names).get("items", [])
            if not items:
                return self.builder.prompt("Create Invoice", "I could not catch the items. Please say item name and quantity.", "items", "create_invoice")
            draft.setdefault("items", []).extend(items)
            total = self._estimate_invoice_total(draft["items"])
            draft["total"] = total
            self._save(state, context, "create_invoice", "confirm")
            return self.builder.build(
                intent="create_invoice",
                title="Confirm Invoice",
                message=f"Invoice total is ₹{total:,.0f}. Confirm?",
                action="confirm_invoice",
                details={"draft_invoice": draft, "total": total},
                session_state={"flow": "create_invoice", "step": "confirm"},
                speech=f"Invoice total is rupees {total:,.0f}. Confirm?",
            )

        if step == "confirm":
            if entities.get("confirmation") is False:
                self._save(state, context, None, None)
                return self.builder.build(
                    intent="create_invoice",
                    title="Invoice Cancelled",
                    message="Invoice draft cancelled.",
                    action="show_message",
                    session_state={"flow": None, "step": None},
                )
            if entities.get("confirmation") is True or self.parser._is_affirmative(text.lower()):
                result = self.invoice_service.send_invoice(draft)
                self._save(state, context, None, None)
                if result.get("status") in {"sent", "pending", "saved"}:
                    invoice = result.get("invoice", {})
                    return self.builder.build(
                        intent="create_invoice",
                        title="Invoice Created",
                        message="Invoice created successfully.",
                        action="view_invoice",
                        details={"invoice": invoice, "workflow_result": result},
                        session_state={"flow": None, "step": None},
                        speech="Invoice created successfully.",
                    )
                return self.builder.error(result.get("error", "Unable to create invoice."), intent="create_invoice")

            return self.builder.prompt("Confirm Invoice", "Please say yes to confirm or no to cancel.", "confirm", "create_invoice")

        self._save(state, context, None, None)
        return self.builder.error("I lost track of the invoice flow.", intent="create_invoice")

    def _start_payment_flow(self, state, context, entities: Dict[str, Any]):
        customer_name = entities.get("customer_name")
        amount = self._coerce_amount(text, entities)
        context.setdefault("payment", {})
        if customer_name:
            context["payment"]["customer_name"] = customer_name
        if amount:
            context["payment"]["amount"] = amount

        if not customer_name:
            self._save(state, context, "record_payment", "customer_name")
            return self.builder.prompt("Record Payment", "Which customer made the payment?", "customer_name", "record_payment")

        if not amount:
            self._save(state, context, "record_payment", "amount")
            return self.builder.prompt("Record Payment", f"How much payment was received from {customer_name}?", "amount", "record_payment")

        return self._finalize_payment(state, context, customer_name, float(amount))

    def _continue_payment_flow(self, state, context, text: str, entities: Dict[str, Any]):
        payment = context.setdefault("payment", {})
        step = state.current_step or "customer_name"
        if step == "customer_name":
            customer_name = entities.get("customer_name") or text.strip()
            payment["customer_name"] = customer_name
            self._save(state, context, "record_payment", "amount")
            return self.builder.prompt("Record Payment", f"How much payment was received from {customer_name}?", "amount", "record_payment")

        if step == "amount":
            amount = self._coerce_amount(text, entities)
            if not amount:
                return self.builder.prompt("Record Payment", "Please tell me the payment amount.", "amount", "record_payment")
            customer_name = payment.get("customer_name") or entities.get("customer_name") or text.strip()
            return self._finalize_payment(state, context, customer_name, float(amount))

        self._save(state, context, None, None)
        return self.builder.error("I lost track of the payment flow.", intent="record_payment")

    def _finalize_payment(self, state, context, customer_name: str, amount: float):
        with session_scope() as session:
            customer = session.query(Customer).filter(Customer.customer_name == customer_name).one_or_none()
            if not customer:
                self._save(state, context, None, None)
                return self.builder.error(f"I couldn't find {customer_name}. Please check the customer name.", intent="record_payment")

            payment = Payment(customer_id=customer.id, amount=amount, payment_date=date.today(), notes=context.get("payment", {}).get("notes"))
            session.add(payment)
            customer.pending_due = max(float(customer.pending_due or 0) - amount, 0)
            customer.last_payment_date = date.today()
            customer.last_payment_amount = amount
            session.add(Transaction(transaction_type="payment", amount=amount, reference=customer_name))
            session.flush()
            payment_dict = payment.to_dict()
            customer_dict = customer.to_dict()

        self._save(state, context, None, None)
        return self.builder.build(
            intent="record_payment",
            title="Payment Recorded",
            message=f"Payment of ₹{amount:,.0f} recorded successfully for {customer_name}.",
            action="view_customer",
            details={"payment": payment_dict, "customer": customer_dict},
            session_state={"flow": None, "step": None},
            speech=f"Payment of rupees {amount:,.0f} recorded successfully.",
        )

    def _handle_inventory_intent(self, intent: str, state, context, text: str, entities: Dict[str, Any]):
        if intent == "low_stock":
            data = self.dashboard.get_low_stock()
            context["last_low_stock_items"] = data.get("items", [])
            self._save(state, context, None, None)
            items = data.get("items", [])
            return self.builder.build(
                intent="low_stock",
                title="Low Stock Alert",
                message=f"You have {len(items)} items running low on stock.",
                action="view_low_stock",
                details={"items": items},
                session_state={"flow": None, "step": None},
                speech=self._speech_for_items("Low stock alert", items),
            )

        if intent == "search_inventory":
            term = entities.get("product_name") or text.replace("search", "").replace("inventory", "").strip()
            matches = [item for item in self.dashboard.get_inventory().get("items", []) if term.lower() in item.get("name", "").lower()]
            self._save(state, context, None, None)
            return self.builder.build(
                intent="search_inventory",
                title="Inventory Search",
                message=f"Found {len(matches)} matching items for '{term}'.",
                action="view_inventory",
                details={"items": matches, "query": term},
                session_state={"flow": None, "step": None},
            )

        if intent == "inventory_summary":
            summary = self.dashboard.get_inventory()
            self._save(state, context, None, None)
            return self.builder.build(
                intent="inventory_summary",
                title="Inventory Summary",
                message=f"Your inventory value is ₹{float(summary.get('total_value', 0) or 0):,.0f}.",
                action="view_inventory",
                details=summary,
                session_state={"flow": None, "step": None},
                speech=f"Inventory summary loaded. Total value is rupees {float(summary.get('total_value', 0) or 0):,.0f}.",
            )

        product_name = entities.get("product_name")
        quantity = entities.get("quantity")

        if intent == "add_inventory":
            if not product_name or not quantity:
                self._save(state, context, "inventory_action", "add")
                context["inventory_action"] = {"intent": "add_inventory", "product_name": product_name, "quantity": quantity}
                self._save(state, context, "inventory_action", "add")
                return self.builder.prompt("Add Inventory", "Tell me the product name and quantity to add.", "add", "inventory_action")
            product = self._find_product(product_name)
            if product:
                product = self.repos.products.update(product, quantity=float(product.quantity or 0) + float(quantity))
            else:
                product = self.repos.products.create(item_name=product_name, quantity=float(quantity), rate=0.0, tax_percent=18.0, reorder_level=0.0)
            self._save(state, context, None, None)
            return self.builder.build(
                intent="add_inventory",
                title="Inventory Updated",
                message=f"Added {quantity} units of {product_name}.",
                action="view_inventory",
                details={"product": product.to_dict()},
                session_state={"flow": None, "step": None},
            )

        if intent == "update_inventory":
            if not product_name or quantity is None:
                self._save(state, context, "inventory_action", "update")
                context["inventory_action"] = {"intent": "update_inventory", "product_name": product_name}
                self._save(state, context, "inventory_action", "update")
                return self.builder.prompt("Update Inventory", "Which product and quantity should I update?", "update", "inventory_action")
            product = self._find_product(product_name)
            if not product:
                return self.builder.error(f"I couldn't find {product_name} in inventory.", intent="update_inventory")
            product = self.repos.products.update(product, quantity=float(quantity))
            self._save(state, context, None, None)
            return self.builder.build(
                intent="update_inventory",
                title="Inventory Updated",
                message=f"Updated {product_name} quantity to {quantity}.",
                action="view_inventory",
                details={"product": product.to_dict()},
                session_state={"flow": None, "step": None},
            )

        if intent == "delete_inventory":
            if not product_name:
                self._save(state, context, "inventory_action", "delete")
                return self.builder.prompt("Delete Inventory", "Which product should I delete?", "delete", "inventory_action")
            product = self._find_product(product_name)
            if not product:
                return self.builder.error(f"I couldn't find {product_name} in inventory.", intent="delete_inventory")
            self.repos.products.delete(product)
            self._save(state, context, None, None)
            return self.builder.build(
                intent="delete_inventory",
                title="Inventory Deleted",
                message=f"Deleted {product_name} from stock.",
                action="view_inventory",
                session_state={"flow": None, "step": None},
            )

        self._save(state, context, None, None)
        return self.builder.error("I could not process that inventory request.", intent=intent)

    def _continue_inventory_flow(self, state, context, text: str, entities: Dict[str, Any]):
        action = context.get("inventory_action", {})
        intent = action.get("intent")
        if intent == "add_inventory":
            product_name = entities.get("product_name") or action.get("product_name") or text.strip()
            quantity = entities.get("quantity") or action.get("quantity")
            if not product_name or not quantity:
                return self.builder.prompt("Add Inventory", "Please tell product name and quantity.", "add", "inventory_action")
            self._save(state, context, None, None)
            return self._handle_inventory_intent("add_inventory", state, context, text, {"product_name": product_name, "quantity": quantity})
        if intent == "update_inventory":
            product_name = entities.get("product_name") or action.get("product_name") or text.strip()
            quantity = entities.get("quantity")
            if not product_name or quantity is None:
                return self.builder.prompt("Update Inventory", "Please tell the product name and new quantity.", "update", "inventory_action")
            self._save(state, context, None, None)
            return self._handle_inventory_intent("update_inventory", state, context, text, {"product_name": product_name, "quantity": quantity})
        if intent == "delete_inventory":
            product_name = entities.get("product_name") or action.get("product_name") or text.strip()
            self._save(state, context, None, None)
            return self._handle_inventory_intent("delete_inventory", state, context, text, {"product_name": product_name})
        self._save(state, context, None, None)
        return self.builder.error("I lost track of the inventory action.", intent="inventory_action")

    def _handle_business_intent(self, intent: str, state, entities: Dict[str, Any]):
        if intent == "today_sales":
            data = self.dashboard.get_today_sales()
            message = f"Today you've made ₹{float(data.get('total', 0) or 0):,.0f} in sales with {int(data.get('count', 0) or 0)} invoices."
            return self.builder.build(intent=intent, title="Today's Sales Summary", message=message, action="view_invoices", details=data, session_state={"flow": None, "step": None}, speech=message)
        if intent == "pending_dues":
            data = self.dashboard.get_pending_dues()
            message = f"You have ₹{float(data.get('total_due', 0) or 0):,.0f} pending from {int(data.get('customer_count', 0) or 0)} customers."
            return self.builder.build(intent=intent, title="Pending Receivables", message=message, action="view_pending", details=data, session_state={"flow": None, "step": None}, speech=message)
        if intent == "overdue_customers":
            data = self.dashboard.get_overdue_customers()
            message = f"Found {len(data.get('customers', []))} overdue customers."
            return self.builder.build(intent=intent, title="Overdue Customers", message=message, action="view_pending", details=data, session_state={"flow": None, "step": None}, speech=message)
        if intent == "recent_transactions":
            data = self.dashboard.get_recent_transactions(limit=10, days=30)
            return self.builder.build(intent=intent, title="Recent Transactions", message=f"Loaded {len(data.get('transactions', []))} recent transactions.", action="view_recent_transactions", details=data, session_state={"flow": None, "step": None})
        if intent == "top_products":
            data = self.dashboard.get_top_products(limit=5)
            return self.builder.build(intent=intent, title="Top Products", message=f"Here are the top {len(data.get('products', []))} products.", action="view_top_products", details=data, session_state={"flow": None, "step": None})
        if intent == "sales_summary":
            data = self.dashboard.get_sales_summary(period="today")
            return self.builder.build(intent=intent, title="Sales Summary", message=f"Sales summary for today is ready.", action="view_sales_summary", details=data, session_state={"flow": None, "step": None})
        return self.builder.error("I could not understand the business question.", intent=intent)

    def _estimate_invoice_total(self, items: List[Dict[str, Any]]) -> float:
        with session_scope() as session:
            total = 0.0
            for item in items:
                name = item.get("name") or item.get("product_name")
                qty = float(item.get("qty", item.get("quantity", 1)) or 1)
                rate = float(item.get("rate", 0) or 0)
                if not rate and name:
                    product = session.query(Product).filter(Product.item_name.ilike(name)).one_or_none()
                    if product:
                        rate = float(product.rate or 0)
                total += qty * rate
            return total

    def _find_product(self, product_name: str):
        return self.repos.products.search(product_name, limit=1)[0] if self.repos.products.search(product_name, limit=1) else None

    def _speech_for_items(self, prefix: str, items: List[Dict[str, Any]]) -> str:
        if not items:
            return prefix
        names = ", ".join(item.get("name", "") for item in items[:3])
        return f"{prefix}. {names} are low."

    def _coerce_amount(self, text: str, entities: Dict[str, Any]) -> Optional[float]:
        amount = entities.get("amount")
        if amount is not None:
            return float(amount)

        stripped = text.strip().replace(",", "")
        if stripped and stripped.replace(".", "", 1).isdigit():
            return float(stripped)

        import re

        match = re.search(r"(\d+(?:\.\d{1,2})?)", stripped)
        if match and any(keyword in stripped.lower() for keyword in ("pay", "payment", "due", "amount", "received", "paid")):
            return float(match.group(1))
        return None
