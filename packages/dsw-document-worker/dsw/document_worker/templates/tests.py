def not_empty(x):
    """Check if a collection is not empty or object is not None"""
    if hasattr(x, '__len__'):
        return len(x) > 0
    return x is not None


def of_type(x, class_name: str):
    """Check if class name is one of the classes of a given object"""
    try:
        classes = {c.__name__.lower() for c in type(x).mro()}
        return class_name.replace('_', '').lower() in classes
    except Exception:
        return False


tests = {
    'not_empty': not_empty,
    'of_type': of_type,
}
