from .dynamic_filter_node import DynamicTextFilterNode

NODE_CLASS_MAPPINGS = {
    "dynamicTextFilter": DynamicTextFilterNode  # 你的节点类映射
}

NODE_DISPLAY_NAMES_MAPPINGS = {
    "dynamicTextFilter": "动态文本过滤节点"  # 在 UI 中显示的名称
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAMES_MAPPINGS']
