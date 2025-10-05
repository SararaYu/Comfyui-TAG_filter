from .dynamic_text_filter_node import DynamicTextFilterNode
from .advanced_dynamic_text_filter_node import AdvancedDynamicTextFilterNode

NODE_CLASS_MAPPINGS = {
    "dynamicTextFilter": DynamicTextFilterNode,
    "advancedDynamicTextFilter": AdvancedDynamicTextFilterNode,
}

NODE_DISPLAY_NAMES_MAPPINGS = {
    "dynamicTextFilter": "动态文本过滤节点",
    "advancedDynamicTextFilter": "动态文本过滤节点（多输出）",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAMES_MAPPINGS']
