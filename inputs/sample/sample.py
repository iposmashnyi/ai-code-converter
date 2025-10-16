"""
Sample Python module for testing code conversion.
This module demonstrates various Python features.
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime


class UserManager:
    """Manages user data and operations."""

    def __init__(self, data_file: str = "users.json"):
        """
        Initialize the UserManager.

        Args:
            data_file: Path to the JSON file storing user data
        """
        self.data_file = data_file
        self.users = self._load_users()

    def _load_users(self) -> List[Dict]:
        """Load users from the data file."""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return []

    def add_user(self, name: str, email: str, age: int) -> Dict:
        """
        Add a new user.

        Args:
            name: User's name
            email: User's email
            age: User's age

        Returns:
            The created user object
        """
        user = {
            "id": len(self.users) + 1,
            "name": name,
            "email": email,
            "age": age,
            "created_at": datetime.now().isoformat()
        }
        self.users.append(user)
        self._save_users()
        return user

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get a user by ID."""
        for user in self.users:
            if user["id"] == user_id:
                return user
        return None

    def update_user(self, user_id: int, **kwargs) -> Optional[Dict]:
        """Update user information."""
        user = self.get_user(user_id)
        if user:
            for key, value in kwargs.items():
                if key in user:
                    user[key] = value
            self._save_users()
            return user
        return None

    def delete_user(self, user_id: int) -> bool:
        """Delete a user by ID."""
        user = self.get_user(user_id)
        if user:
            self.users.remove(user)
            self._save_users()
            return True
        return False

    def list_users(self, min_age: Optional[int] = None) -> List[Dict]:
        """
        List all users, optionally filtered by minimum age.

        Args:
            min_age: Optional minimum age filter

        Returns:
            List of users matching the criteria
        """
        if min_age is None:
            return self.users

        filtered_users = []
        for user in self.users:
            if user["age"] >= min_age:
                filtered_users.append(user)
        return filtered_users

    def _save_users(self) -> None:
        """Save users to the data file."""
        with open(self.data_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    def get_statistics(self) -> Dict:
        """Get statistics about users."""
        if not self.users:
            return {
                "total": 0,
                "average_age": 0,
                "oldest": None,
                "youngest": None
            }

        ages = [user["age"] for user in self.users]
        return {
            "total": len(self.users),
            "average_age": sum(ages) / len(ages),
            "oldest": max(ages),
            "youngest": min(ages)
        }


def process_data(items: List[int], threshold: int = 10) -> Dict:
    """
    Process a list of numbers and return analysis.

    Args:
        items: List of numbers to process
        threshold: Threshold value for filtering

    Returns:
        Dictionary with processed results
    """
    filtered = [x for x in items if x > threshold]
    doubled = [x * 2 for x in filtered]

    result = {
        "original_count": len(items),
        "filtered_count": len(filtered),
        "filtered_items": filtered,
        "doubled_items": doubled,
        "sum": sum(doubled) if doubled else 0
    }

    return result


# Global configuration
CONFIG = {
    "app_name": "User Management System",
    "version": "1.0.0",
    "debug": False
}


def main():
    """Main function to demonstrate usage."""
    # Create user manager
    manager = UserManager("test_users.json")

    # Add some users
    manager.add_user("Alice", "alice@example.com", 25)
    manager.add_user("Bob", "bob@example.com", 30)
    manager.add_user("Charlie", "charlie@example.com", 35)

    # List users
    print("All users:")
    for user in manager.list_users():
        print(f"  - {user['name']} ({user['age']} years)")

    # Get statistics
    stats = manager.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total users: {stats['total']}")
    print(f"  Average age: {stats['average_age']:.1f}")

    # Process some data
    numbers = [5, 15, 25, 8, 35, 12, 45]
    processed = process_data(numbers, threshold=20)
    print(f"\nProcessed data:")
    print(f"  Filtered items: {processed['filtered_items']}")
    print(f"  Sum of doubled: {processed['sum']}")


if __name__ == "__main__":
    main()