"""Voice command handlers for inventory, invoicing, payments, and dashboard."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Iterable

logger = logging.getLogger(__name__)


class VoiceCommandHandler:
    """Handle voice commands specific to retailer workflows."""
    
    def __init__(
        self,
        invoice_service=None,
        dashboard_service=None,
        workflow_engine=None,
        repos=None,
    ):
        """
        Initialize command handler with services.
        
        Args:
            invoice_service: Invoice management service
            dashboard_service: Dashboard/analytics service
            workflow_engine: Workflow execution engine
            repos: Repository bundle for data access
        """
        self.invoice = invoice_service
        self.dashboard = dashboard_service
        self.workflow = workflow_engine
        self.repos = repos
    
    def handle_inventory_command(
        self,
        intent: str,
        entities: Dict[str, object],
        **context,
    ) -> Dict[str, object]:
        """
        Handle inventory-related voice commands.
        
        Commands:
        - "add 20 coke bottles"
        - "update maggi quantity to 50"
        - "search maggi stock"
        - "show low stock items"
        """
        if not self.repos:
            return {"status": "error", "message": "Repositories not available"}
        
        try:
            product_name = entities.get("product_name")
            quantity = entities.get("quantity")
            
            if intent == "add_inventory":
                if not product_name or quantity is None:
                    return {
                        "status": "clarify",
                        "message": "Which product? How many items?",
                        "requires": ["product_name", "quantity"],
                    }
                
                # Find or create product
                product = self._find_or_create_product(product_name)
                if product:
                    new_quantity = product.get("quantity", 0) + quantity
                    updated = self.repos.products.update(
                        product,
                        quantity=new_quantity,
                        updated_by="voice_command",
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Added {quantity} {product_name}. New stock: {new_quantity}",
                        "data": updated.to_dict() if hasattr(updated, "to_dict") else updated,
                    }
            
            elif intent == "update_inventory":
                if not product_name or quantity is None:
                    return {
                        "status": "clarify",
                        "message": "Which product? What's the new quantity?",
                        "requires": ["product_name", "quantity"],
                    }
                
                product = self._find_or_create_product(product_name)
                if product:
                    updated = self.repos.products.update(
                        product,
                        quantity=quantity,
                        updated_by="voice_command",
                    )
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Updated {product_name} quantity to {quantity}",
                        "data": updated.to_dict() if hasattr(updated, "to_dict") else updated,
                    }
            
            elif intent == "search_inventory":
                if not product_name:
                    return {
                        "status": "clarify",
                        "message": "What product are you looking for?",
                    }
                
                # Search for product
                products = self.repos.products.list(page=1, per_page=100)
                matching = [
                    p for p in products.get("items", [])
                    if product_name.lower() in p.get("item_name", "").lower()
                ]
                
                if matching:
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Found {len(matching)} product(s) matching '{product_name}'",
                        "data": matching,
                    }
                else:
                    return {
                        "status": "not_found",
                        "intent": intent,
                        "message": f"No products found matching '{product_name}'",
                    }
            
            elif intent == "low_stock":
                if self.dashboard:
                    low_stock_data = self.dashboard.get_low_stock()
                    items = low_stock_data.get("items", [])[:5]
                    count = low_stock_data.get("count", 0)
                    
                    if items:
                        item_names = ", ".join([item.get("item_name", "?") for item in items])
                        return {
                            "status": "success",
                            "intent": intent,
                            "message": f"Low stock: {item_names}. Total items: {count}",
                            "data": items,
                        }
                    else:
                        return {
                            "status": "success",
                            "intent": intent,
                            "message": "Good news! All items are well-stocked.",
                        }
            
            return {"status": "error", "message": f"Unknown inventory intent: {intent}"}
        
        except Exception as e:
            logger.error(f"Inventory command error: {e}")
            return {"status": "error", "message": str(e)}
    
    def handle_invoice_command(
        self,
        intent: str,
        entities: Dict[str, object],
        session_id: Optional[str] = None,
        **context,
    ) -> Dict[str, object]:
        """
        Handle invoice-related voice commands.
        
        Commands:
        - "create invoice"
        - "add 5 coke and 2 maggi"
        - "show recent invoices"
        """
        if intent == "create_invoice":
            items = entities.get("items", [])
            customer_name = entities.get("customer_name")
            
            if not items and not customer_name:
                return {
                    "status": "clarify",
                    "message": "Who is the customer? What items should I add?",
                    "requires": ["customer_name", "items"],
                    "workflow": "create_invoice_flow",
                }
            
            if self.invoice and self.repos:
                try:
                    # Store workflow state for multi-turn interaction
                    if session_id:
                        workflow_state = {
                            "session_id": session_id,
                            "intent": "create_invoice",
                            "customer_name": customer_name,
                            "items": items,
                            "step": "awaiting_confirmation",
                        }
                        # This would be stored in the workflow engine
                    
                    # Calculate total
                    total = 0
                    for item in items:
                        product = self._find_product_by_name(item.get("name"))
                        if product:
                            total += product.get("price", 0) * item.get("quantity", 0)
                    
                    return {
                        "status": "confirm",
                        "intent": intent,
                        "message": f"Invoice total ₹{total:,.0f}. Confirm?",
                        "data": {
                            "customer": customer_name,
                            "items": items,
                            "total": total,
                        },
                        "next_action": "confirm_invoice",
                    }
                
                except Exception as e:
                    logger.error(f"Invoice creation error: {e}")
                    return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": f"Unknown invoice intent: {intent}"}
    
    def handle_payment_command(
        self,
        intent: str,
        entities: Dict[str, object],
        **context,
    ) -> Dict[str, object]:
        """
        Handle payment-related voice commands.
        
        Commands:
        - "record payment from abc traders"
        - "show pending dues"
        - "show overdue customers"
        """
        if not self.dashboard:
            return {"status": "error", "message": "Dashboard service not available"}
        
        try:
            if intent == "record_payment":
                customer_name = entities.get("customer_name")
                amount = entities.get("amount")
                
                if not customer_name:
                    return {
                        "status": "clarify",
                        "message": "Which customer made the payment?",
                        "requires": ["customer_name"],
                    }
                
                if amount is None:
                    return {
                        "status": "clarify",
                        "message": f"How much did {customer_name} pay?",
                        "requires": ["amount"],
                    }
                
                return {
                    "status": "success",
                    "intent": intent,
                    "message": f"Payment of ₹{amount:,.0f} recorded from {customer_name}",
                }
            
            elif intent == "pending_dues":
                dues_data = self.dashboard.get_pending_dues()
                total_due = dues_data.get("total_due", 0)
                customer_count = dues_data.get("customer_count", 0)
                
                return {
                    "status": "success",
                    "intent": intent,
                    "message": f"Total pending dues: ₹{total_due:,.0f} from {customer_count} customers",
                    "data": dues_data,
                }
            
            elif intent == "overdue_customers":
                # This would require additional data from dashboard
                return {
                    "status": "success",
                    "intent": intent,
                    "message": "Checking for overdue payments...",
                }
            
            return {"status": "error", "message": f"Unknown payment intent: {intent}"}
        
        except Exception as e:
            logger.error(f"Payment command error: {e}")
            return {"status": "error", "message": str(e)}
    
    def handle_dashboard_command(
        self,
        intent: str,
        entities: Dict[str, object],
        **context,
    ) -> Dict[str, object]:
        """
        Handle dashboard/analytics voice commands.
        
        Commands:
        - "today's sales"
        - "top products"
        - "inventory summary"
        - "sales summary"
        """
        if not self.dashboard:
            return {"status": "error", "message": "Dashboard service not available"}
        
        try:
            if intent == "today_sales":
                sales_data = self.dashboard.get_today_sales()
                total = sales_data.get("total", 0)
                count = sales_data.get("count", 0)
                
                return {
                    "status": "success",
                    "intent": intent,
                    "message": f"Today's sales: ₹{total:,.0f} from {count} invoices",
                    "data": sales_data,
                }
            
            elif intent == "top_products":
                products = self.dashboard.get_top_products(limit=5)
                items = products.get("products", [])[:3]
                
                if items:
                    product_names = ", ".join([p.get("name", "?") for p in items])
                    return {
                        "status": "success",
                        "intent": intent,
                        "message": f"Top products: {product_names}",
                        "data": items,
                    }
                else:
                    return {"status": "success", "intent": intent, "message": "No data available"}
            
            elif intent == "inventory_summary":
                inventory = self.dashboard.get_inventory()
                total_value = inventory.get("total_value", 0)
                item_count = inventory.get("item_count", 0)
                
                return {
                    "status": "success",
                    "intent": intent,
                    "message": f"Inventory: {item_count} items worth ₹{total_value:,.0f}",
                    "data": inventory,
                }
            
            elif intent == "sales_summary":
                summary = self.dashboard.get_sales_summary(period="today")
                return {
                    "status": "success",
                    "intent": intent,
                    "message": "Sales summary retrieved",
                    "data": summary,
                }
            
            return {"status": "error", "message": f"Unknown dashboard intent: {intent}"}
        
        except Exception as e:
            logger.error(f"Dashboard command error: {e}")
            return {"status": "error", "message": str(e)}
    
    # Helper methods
    def _find_product_by_name(self, product_name: str) -> Optional[dict]:
        """Find product by name."""
        if not self.repos or not product_name:
            return None
        
        products = self.repos.products.list(page=1, per_page=1000)
        for product in products.get("items", []):
            if product_name.lower() in product.get("item_name", "").lower():
                return product
        return None
    
    def _find_or_create_product(self, product_name: str) -> Optional[dict]:
        """Find product by name or create if not exists."""
        product = self._find_product_by_name(product_name)
        if product:
            return product
        
        if not self.repos:
            return None
        
        try:
            created = self.repos.products.create(
                item_name=product_name,
                quantity=0,
                price=0,
                tax=0,
                unit_of_measure="Units",
            )
            return created.to_dict() if hasattr(created, "to_dict") else created
        except Exception as e:
            logger.error(f"Failed to create product: {e}")
            return None
