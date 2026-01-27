# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Action Handler System using Strategy Pattern.

This module provides a pluggable architecture for action type handlers,
allowing third-party apps to register custom action types without modifying
the core engine.

Usage:
    from flexirule.ruleflow.core.action_handlers import HandlerRegistry, ActionHandler

    class MyCustomHandler(ActionHandler):
        action_type = "My Custom Action"

        def execute(self, action, context, engine):
            # Custom logic here
            return result, next_action_id

    HandlerRegistry.register(MyCustomHandler())
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from flexirule.ruleflow.core.engine import RuleEngine


class ActionHandler(ABC):
    """
    Abstract base class for all action handlers.

    Each handler is responsible for executing a specific action type.
    Handlers are stateless singletons registered with the HandlerRegistry.
    """

    action_type: str = None  # Must be set by subclass

    @abstractmethod
    def execute(
        self, action, context: dict, engine: "RuleEngine"
    ) -> Tuple[Any, Optional[str]]:
        """
        Execute the action.

        Args:
            action: The Rule Action row (child table row)
            context: Execution context dict with doc, vars, frappe, etc.
            engine: Reference to the RuleEngine instance for utility methods

        Returns:
            Tuple of (result, next_action_id)
            - result: The execution result (can be any type)
            - next_action_id: ID of the next action to execute, or None to stop
        """
        pass

    def validate(self, action, context: dict) -> list:
        """
        Optional validation before execution.

        Override this method to add pre-execution validation.

        Args:
            action: The Rule Action row
            context: Execution context

        Returns:
            List of error message strings (empty if valid)
        """
        return []

    def __repr__(self):
        return f"<{self.__class__.__name__}(action_type='{self.action_type}')>"


class HandlerRegistry:
    """
    Registry for action handlers.

    This registry allows plugin-based extension of action types.
    Third-party apps can register custom handlers that will be
    automatically picked up by the RuleEngine.
    """

    _handlers: dict = {}
    _initialized: bool = False

    @classmethod
    def register(cls, handler: ActionHandler) -> None:
        """
        Register a handler for its action type.

        Args:
            handler: An ActionHandler instance

        Raises:
            ValueError: If handler has no action_type set
        """
        if not handler.action_type:
            raise ValueError(
                f"Handler {handler.__class__.__name__} must set 'action_type' class attribute"
            )
        cls._handlers[handler.action_type] = handler

    @classmethod
    def get(cls, action_type: str) -> Optional[ActionHandler]:
        """
        Get the handler for an action type.

        Args:
            action_type: The action type string (e.g., "Condition", "Process")

        Returns:
            The registered handler, or None if not found
        """
        cls._ensure_initialized()
        return cls._handlers.get(action_type)

    @classmethod
    def all(cls) -> dict:
        """
        Get all registered handlers.

        Returns:
            Dict mapping action_type -> handler instance
        """
        cls._ensure_initialized()
        return cls._handlers.copy()

    @classmethod
    def action_types(cls) -> list:
        """
        Get list of all registered action types.

        Returns:
            List of action type strings
        """
        cls._ensure_initialized()
        return list(cls._handlers.keys())

    @classmethod
    def _ensure_initialized(cls) -> None:
        """
        Lazily load all built-in handlers on first access.

        This avoids circular imports and ensures handlers are loaded
        when needed.
        """
        if cls._initialized:
            return

        # Import all built-in handlers to trigger registration
        from flexirule.ruleflow.core.action_handlers import (
            condition,
            loop,
            process,
            simple_actions,
            sub_rule,
            switch,
        )

        cls._initialized = True

    @classmethod
    def reset(cls) -> None:
        """
        Reset the registry (for testing purposes).
        """
        cls._handlers = {}
        cls._initialized = False
