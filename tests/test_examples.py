"""
Test file for agentic code review - contains various code patterns for analysis.
"""

def calculate_sum(numbers):
    """Calculate sum of numbers - intentionally simple for testing."""
    total = 0
    for num in numbers:
        total = total + num  # Could be optimized with sum() or operator.add
    return total


def process_user_data(user_dict):
    """Process user data with potential improvements."""
    # Not using type hints
    name = user_dict.get('name')
    email = user_dict.get('email')
    age = user_dict.get('age')
    
    # Repeated code pattern
    if name:
        print(f"Name: {name}")
    if email:
        print(f"Email: {email}")
    if age:
        print(f"Age: {age}")
    
    return {"name": name, "email": email, "age": age}


class DataHandler:
    """Handle data operations with room for improvement."""
    
    def __init__(self, data):
        self.data = data
        self.results = []
    
    def filter_data(self, key):
        """Filter data by key value."""
        filtered = []
        for item in self.data:
            if item.get(key):
                filtered.append(item)
        return filtered
    
    def save_results(self, filename):
        """Save results to file."""
        with open(filename, 'w') as f:
            f.write(str(self.results))
        # No error handling


def validate_email(email):
    """Simple email validation."""
    # Naive validation
    if '@' in email and '.' in email:
        return True
    return False


# Global variable (could be refactored)
CACHE = {}


def get_cached_value(key):
    """Get value from global cache."""
    return CACHE.get(key)


def set_cached_value(key, value):
    """Set value in global cache."""
    CACHE[key] = value
    return True
