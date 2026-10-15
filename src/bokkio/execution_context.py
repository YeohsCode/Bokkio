"""Causal log context, independent of execution policy and model decisions."""
from contextvars import ContextVar

parent_operation = ContextVar('bokkio_parent_operation', default=None)
workflow_step = ContextVar('bokkio_workflow_step', default=None)
