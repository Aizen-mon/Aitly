"""Multi-step voice workflows for conversational business processes."""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowStepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class VoiceWorkflowContext:
    """Context for multi-step voice workflow."""
    
    def __init__(self, session_id: str, workflow_type: str):
        """Initialize workflow context."""
        self.session_id = session_id
        self.workflow_type = workflow_type
        self.current_step = 0
        self.steps: Dict[int, Dict[str, object]] = {}
        self.data: Dict[str, object] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed = False
        self.history: List[Dict[str, object]] = []
    
    def add_step(self, step_id: int, prompt: str, required_fields: List[str]) -> None:
        """Add a workflow step."""
        self.steps[step_id] = {
            "id": step_id,
            "prompt": prompt,
            "required_fields": required_fields,
            "status": WorkflowStepStatus.PENDING.value,
            "response": None,
            "extracted_data": {},
        }
    
    def set_step_active(self, step_id: int) -> None:
        """Mark step as active."""
        if step_id in self.steps:
            self.steps[step_id]["status"] = WorkflowStepStatus.ACTIVE.value
            self.current_step = step_id
    
    def set_step_completed(self, step_id: int, response: str, extracted_data: Dict) -> None:
        """Mark step as completed with response."""
        if step_id in self.steps:
            self.steps[step_id]["status"] = WorkflowStepStatus.COMPLETED.value
            self.steps[step_id]["response"] = response
            self.steps[step_id]["extracted_data"] = extracted_data
            self.data.update(extracted_data)
            self.updated_at = datetime.now()
            self.history.append({
                "step": step_id,
                "response": response,
                "timestamp": datetime.now().isoformat(),
            })
    
    def to_dict(self) -> Dict[str, object]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "workflow_type": self.workflow_type,
            "current_step": self.current_step,
            "steps": self.steps,
            "data": self.data,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "history": self.history,
        }


class MultiStepVoiceWorkflow:
    """Handle multi-step conversational voice workflows."""
    
    # Define standard workflows
    INVOICE_CREATION_FLOW = {
        0: {"prompt": "Who is the customer?", "required": ["customer_name"]},
        1: {"prompt": "What items should I add?", "required": ["items"]},
        2: {"prompt": "Confirm total ₹{total}?", "required": ["confirmation"]},
        3: {"prompt": "Invoice created successfully!", "required": []},
    }
    
    PAYMENT_RECORDING_FLOW = {
        0: {"prompt": "Which customer made the payment?", "required": ["customer_name"]},
        1: {"prompt": "How much did they pay?", "required": ["amount"]},
        2: {"prompt": "Is this amount correct?", "required": ["confirmation"]},
    }
    
    ADD_INVENTORY_FLOW = {
        0: {"prompt": "Which product?", "required": ["product_name"]},
        1: {"prompt": "How many items?", "required": ["quantity"]},
        2: {"prompt": "Confirm adding {quantity} {product}?", "required": ["confirmation"]},
    }
    
    WORKFLOWS = {
        "create_invoice": INVOICE_CREATION_FLOW,
        "record_payment": PAYMENT_RECORDING_FLOW,
        "add_inventory": ADD_INVENTORY_FLOW,
    }
    
    def __init__(self, repos=None, nlp_service=None, command_handler=None):
        """Initialize multi-step workflow engine."""
        self.repos = repos
        self.nlp = nlp_service
        self.commands = command_handler
        self.active_workflows: Dict[str, VoiceWorkflowContext] = {}
    
    def start_workflow(self, session_id: str, workflow_type: str) -> Optional[VoiceWorkflowContext]:
        """Start a multi-step workflow."""
        if workflow_type not in self.WORKFLOWS:
            return None
        
        context = VoiceWorkflowContext(session_id, workflow_type)
        flow_steps = self.WORKFLOWS[workflow_type]
        
        for step_id, step_config in flow_steps.items():
            context.add_step(
                step_id,
                step_config["prompt"],
                step_config["required"],
            )
        
        context.set_step_active(0)
        self.active_workflows[session_id] = context
        
        logger.info(f"Started {workflow_type} workflow for session {session_id}")
        return context
    
    def get_workflow(self, session_id: str) -> Optional[VoiceWorkflowContext]:
        """Get active workflow for session."""
        return self.active_workflows.get(session_id)
    
    def process_step_response(
        self,
        session_id: str,
        user_response: str,
        extracted_data: Dict[str, object],
    ) -> Dict[str, object]:
        """
        Process user response in active workflow.
        
        Returns:
            - next prompt if more steps needed
            - final result if workflow completed
            - error if step fails
        """
        workflow = self.get_workflow(session_id)
        if not workflow:
            return {
                "status": "error",
                "message": "No active workflow found",
            }
        
        current_step_id = workflow.current_step
        current_step = workflow.steps.get(current_step_id)
        
        if not current_step:
            return {
                "status": "error",
                "message": "Invalid workflow state",
            }
        
        # Mark current step as completed
        workflow.set_step_completed(current_step_id, user_response, extracted_data)
        
        # Check if workflow is complete
        if current_step_id == len(workflow.steps) - 1:
            workflow.completed = True
            
            # Execute the workflow's action
            result = self._execute_workflow(workflow)
            
            del self.active_workflows[session_id]
            logger.info(f"Completed {workflow.workflow_type} workflow for {session_id}")
            
            return result
        
        # Move to next step
        next_step_id = current_step_id + 1
        next_step = workflow.steps.get(next_step_id)
        
        if next_step:
            workflow.set_step_active(next_step_id)
            
            # Format prompt with collected data
            prompt = next_step["prompt"]
            if "{total}" in prompt:
                total = workflow.data.get("total", 0)
                prompt = prompt.format(total=total)
            elif "{quantity}" in prompt and "{product}" in prompt:
                quantity = workflow.data.get("quantity", 0)
                product = workflow.data.get("product_name", "item")
                prompt = prompt.format(quantity=quantity, product=product)
            
            return {
                "status": "continue",
                "message": prompt,
                "step": next_step_id,
                "workflow_data": workflow.data,
            }
        
        return {
            "status": "error",
            "message": "Workflow step not found",
        }
    
    def _execute_workflow(self, context: VoiceWorkflowContext) -> Dict[str, object]:
        """Execute the business action for completed workflow."""
        workflow_type = context.workflow_type
        data = context.data
        
        try:
            if workflow_type == "create_invoice":
                return self._execute_invoice_creation(data)
            elif workflow_type == "record_payment":
                return self._execute_payment_recording(data)
            elif workflow_type == "add_inventory":
                return self._execute_inventory_addition(data)
            else:
                return {
                    "status": "error",
                    "message": f"Unknown workflow: {workflow_type}",
                }
        
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "status": "error",
                "message": f"Execution failed: {str(e)}",
            }
    
    def _execute_invoice_creation(self, data: Dict[str, object]) -> Dict[str, object]:
        """Execute invoice creation workflow."""
        if not self.commands:
            return {"status": "error", "message": "Command handler not available"}
        
        result = self.commands.handle_invoice_command(
            "create_invoice",
            data,
        )
        
        return {
            "status": "success",
            "action": "invoice_created",
            "message": f"Invoice created for {data.get('customer_name')}",
            "data": result,
        }
    
    def _execute_payment_recording(self, data: Dict[str, object]) -> Dict[str, object]:
        """Execute payment recording workflow."""
        if not self.commands:
            return {"status": "error", "message": "Command handler not available"}
        
        result = self.commands.handle_payment_command(
            "record_payment",
            data,
        )
        
        return {
            "status": "success",
            "action": "payment_recorded",
            "message": f"Payment of ₹{data.get('amount')} recorded",
            "data": result,
        }
    
    def _execute_inventory_addition(self, data: Dict[str, object]) -> Dict[str, object]:
        """Execute inventory addition workflow."""
        if not self.commands:
            return {"status": "error", "message": "Command handler not available"}
        
        result = self.commands.handle_inventory_command(
            "add_inventory",
            data,
        )
        
        return {
            "status": "success",
            "action": "inventory_added",
            "message": f"Added {data.get('quantity')} {data.get('product_name')}",
            "data": result,
        }
    
    def handle_clarification_request(
        self,
        session_id: str,
        missing_fields: List[str],
    ) -> Dict[str, object]:
        """Handle requests for clarification."""
        workflow = self.get_workflow(session_id)
        if not workflow:
            return {"status": "error", "message": "No active workflow"}
        
        current_step = workflow.steps.get(workflow.current_step)
        if not current_step:
            return {"status": "error", "message": "Invalid step"}
        
        # Build clarification message
        missing_labels = {
            "customer_name": "customer name",
            "amount": "amount",
            "quantity": "quantity",
            "product_name": "product name",
            "items": "items to add",
            "confirmation": "confirmation",
        }
        
        missing_text = " and ".join([missing_labels.get(f, f) for f in missing_fields])
        
        return {
            "status": "clarify",
            "message": f"Please specify: {missing_text}",
            "missing_fields": missing_fields,
        }
    
    def cancel_workflow(self, session_id: str) -> Dict[str, object]:
        """Cancel an active workflow."""
        if session_id in self.active_workflows:
            workflow = self.active_workflows[session_id]
            del self.active_workflows[session_id]
            
            return {
                "status": "cancelled",
                "message": f"{workflow.workflow_type} workflow cancelled",
            }
        
        return {
            "status": "error",
            "message": "No active workflow to cancel",
        }
    
    def get_all_workflows(self) -> Dict[str, Dict[str, object]]:
        """Get all available workflow templates."""
        return {
            workflow_name: {
                "name": workflow_name,
                "steps": len(steps),
                "description": self._get_workflow_description(workflow_name),
            }
            for workflow_name, steps in self.WORKFLOWS.items()
        }
    
    @staticmethod
    def _get_workflow_description(workflow_name: str) -> str:
        """Get human-readable description of workflow."""
        descriptions = {
            "create_invoice": "Create a new invoice with items and customer",
            "record_payment": "Record a payment from a customer",
            "add_inventory": "Add new inventory items to stock",
        }
        return descriptions.get(workflow_name, "Unknown workflow")
