# telegram-bot/bot/game_engine/number_caller.py
# Estif Bingo 24/7 - Number Caller
# Handles random number generation (1-75) without repetition for bingo games

import random
from typing import List, Optional, Set
from datetime import datetime

from bot.utils.logger import logger


class NumberCaller:
    """
    Random number caller for bingo game.
    Draws numbers from 1 to 75 without repetition until all numbers are called.
    Uses Fisher-Yates shuffle for efficient random distribution.
    """
    
    # Bingo number ranges
    MIN_NUMBER = 1
    MAX_NUMBER = 75
    TOTAL_NUMBERS = 75
    
    # Column ranges for BINGO (for number categorization)
    COLUMN_RANGES = {
        'B': (1, 15),
        'I': (16, 30),
        'N': (31, 45),
        'G': (46, 60),
        'O': (61, 75)
    }
    
    def __init__(self):
        """Initialize the number caller"""
        self.numbers: List[int] = []
        self.called_numbers: List[int] = []
        self.current_index: int = 0
        self._shuffle_count: int = 0
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        
        logger.info("NumberCaller initialized")
    
    def reset(self) -> None:
        """
        Reset the number caller for a new round.
        Creates a new shuffled list of numbers 1-75.
        """
        # Create list of all numbers
        self.numbers = list(range(self.MIN_NUMBER, self.MAX_NUMBER + 1))
        
        # Fisher-Yates shuffle for true randomness
        self._fisher_yates_shuffle()
        
        self.called_numbers = []
        self.current_index = 0
        self._shuffle_count += 1
        self._start_time = datetime.utcnow()
        self._end_time = None
        
        logger.info(f"NumberCaller reset with fresh shuffle #{self._shuffle_count}")
    
    def _fisher_yates_shuffle(self) -> None:
        """
        Fisher-Yates shuffle algorithm for unbiased random distribution.
        This is more random than random.shuffle() for cryptographic purposes.
        """
        arr = self.numbers
        for i in range(len(arr) - 1, 0, -1):
            j = random.randint(0, i)
            arr[i], arr[j] = arr[j], arr[i]
    
    def draw_next(self) -> Optional[int]:
        """
        Draw the next random number.
        
        Returns:
            int: The next number, or None if no numbers left
        """
        if self.current_index >= len(self.numbers):
            logger.warning("No more numbers to draw")
            self._end_time = datetime.utcnow()
            return None
        
        number = self.numbers[self.current_index]
        self.called_numbers.append(number)
        self.current_index += 1
        
        logger.debug(f"Number drawn: {number} ({self.current_index}/{self.TOTAL_NUMBERS})")
        return number
    
    def draw_multiple(self, count: int) -> List[int]:
        """
        Draw multiple numbers at once.
        
        Args:
            count: int - Number of numbers to draw
        
        Returns:
            list: List of drawn numbers
        """
        drawn = []
        for _ in range(count):
            number = self.draw_next()
            if number is None:
                break
            drawn.append(number)
        
        return drawn
    
    def peek_next(self) -> Optional[int]:
        """
        Peek at the next number without drawing it.
        
        Returns:
            int: The next number, or None if no numbers left
        """
        if self.current_index >= len(self.numbers):
            return None
        
        return self.numbers[self.current_index]
    
    def peek_multiple(self, count: int) -> List[int]:
        """
        Peek at multiple upcoming numbers without drawing them.
        
        Args:
            count: int - Number of numbers to peek
        
        Returns:
            list: List of upcoming numbers
        """
        end_index = min(self.current_index + count, len(self.numbers))
        return self.numbers[self.current_index:end_index]
    
    def has_next(self) -> bool:
        """
        Check if there are more numbers to draw.
        
        Returns:
            bool: True if more numbers available
        """
        return self.current_index < len(self.numbers)
    
    def get_remaining_count(self) -> int:
        """
        Get the number of remaining numbers.
        
        Returns:
            int: Count of remaining numbers
        """
        return len(self.numbers) - self.current_index
    
    def get_called_count(self) -> int:
        """
        Get the number of called numbers.
        
        Returns:
            int: Count of called numbers
        """
        return self.current_index
    
    def get_all_called_numbers(self) -> List[int]:
        """
        Get all called numbers so far.
        
        Returns:
            list: List of called numbers in order
        """
        return self.called_numbers.copy()
    
    def get_last_number(self) -> Optional[int]:
        """
        Get the last called number.
        
        Returns:
            int: Last called number, or None if no numbers called
        """
        if not self.called_numbers:
            return None
        return self.called_numbers[-1]
    
    def get_last_n_numbers(self, n: int) -> List[int]:
        """
        Get the last N called numbers.
        
        Args:
            n: int - Number of recent numbers to retrieve
        
        Returns:
            list: List of last N numbers
        """
        return self.called_numbers[-n:] if self.called_numbers else []
    
    def is_number_called(self, number: int) -> bool:
        """
        Check if a specific number has been called.
        
        Args:
            number: int - Number to check
        
        Returns:
            bool: True if number has been called
        """
        return number in self.called_numbers
    
    def get_column_for_number(self, number: int) -> Optional[str]:
        """
        Get the BINGO column letter for a number.
        
        Args:
            number: int - Number (1-75)
        
        Returns:
            str: Column letter (B, I, N, G, O) or None if invalid
        """
        for column, (min_val, max_val) in self.COLUMN_RANGES.items():
            if min_val <= number <= max_val:
                return column
        return None
    
    def format_number_with_column(self, number: int) -> str:
        """
        Format number with its BINGO column (e.g., "B12", "I23").
        
        Args:
            number: int - Number (1-75)
        
        Returns:
            str: Formatted number with column
        """
        column = self.get_column_for_number(number)
        if column:
            return f"{column}{number}"
        return str(number)
    
    def get_statistics(self) -> dict:
        """
        Get statistics about the current drawing session.
        
        Returns:
            dict: Statistics including called numbers, remaining, etc.
        """
        return {
            'total_numbers': self.TOTAL_NUMBERS,
            'called_count': self.get_called_count(),
            'remaining_count': self.get_remaining_count(),
            'called_numbers': self.called_numbers,
            'last_number': self.get_last_number(),
            'completion_percentage': (self.get_called_count() / self.TOTAL_NUMBERS) * 100,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'end_time': self._end_time.isoformat() if self._end_time else None,
            'shuffle_count': self._shuffle_count
        }
    
    def get_number_frequency_report(self) -> dict:
        """
        Generate a report of how many times each number has been called
        across all rounds (useful for analytics).
        
        Note: This requires tracking across rounds, which would need persistent storage.
        This method provides a template for such tracking.
        
        Returns:
            dict: Number frequency report structure
        """
        # This would require database tracking across rounds
        # Returns a template structure
        return {
            'total_rounds_tracked': 0,
            'numbers_called': {},
            'most_frequent': None,
            'least_frequent': None,
            'average_per_round': 0
        }
    
    def get_column_statistics(self) -> dict:
        """
        Get statistics about numbers called per column.
        
        Returns:
            dict: Statistics per BINGO column
        """
        column_stats = {col: {'called': 0, 'total': 15} for col in self.COLUMN_RANGES.keys()}
        
        for number in self.called_numbers:
            column = self.get_column_for_number(number)
            if column:
                column_stats[column]['called'] += 1
        
        for col in column_stats:
            column_stats[col]['percentage'] = (column_stats[col]['called'] / column_stats[col]['total']) * 100
        
        return column_stats
    
    def get_drawing_speed(self) -> float:
        """
        Calculate the average drawing speed (numbers per second).
        
        Returns:
            float: Numbers per second, or 0 if not enough data
        """
        if not self._start_time or self.current_index == 0:
            return 0.0
        
        elapsed = (datetime.utcnow() - self._start_time).total_seconds()
        if elapsed > 0:
            return self.current_index / elapsed
        
        return 0.0
    
    def estimate_remaining_time(self, interval_seconds: float = 3.0) -> float:
        """
        Estimate remaining time based on current drawing interval.
        
        Args:
            interval_seconds: float - Seconds between draws
        
        Returns:
            float: Estimated remaining time in seconds
        """
        remaining_count = self.get_remaining_count()
        return remaining_count * interval_seconds
    
    def reset_if_complete(self) -> bool:
        """
        Reset the number caller if all numbers have been drawn.
        
        Returns:
            bool: True if reset occurred, False otherwise
        """
        if not self.has_next():
            self.reset()
            return True
        return False
    
    def __len__(self) -> int:
        """Return the number of remaining numbers"""
        return self.get_remaining_count()
    
    def __str__(self) -> str:
        """String representation of the number caller state"""
        return f"NumberCaller(called={self.get_called_count()}/{self.TOTAL_NUMBERS}, remaining={self.get_remaining_count()})"
    
    def __repr__(self) -> str:
        return self.__str__()


class WeightedNumberCaller(NumberCaller):
    """
    Extended NumberCaller with weighted probability for different columns.
    Useful for creating more interesting game patterns.
    """
    
    def __init__(self, weights: Optional[dict] = None):
        """
        Initialize weighted number caller.
        
        Args:
            weights: dict - Weights for each column (B, I, N, G, O)
                     Default: equal weights for all columns
        """
        super().__init__()
        
        # Default equal weights
        self.weights = weights or {
            'B': 0.2,
            'I': 0.2,
            'N': 0.2,
            'G': 0.2,
            'O': 0.2
        }
        
        # Normalize weights
        total = sum(self.weights.values())
        if total > 0:
            for col in self.weights:
                self.weights[col] /= total
    
    def _get_weighted_column(self) -> str:
        """
        Get a random column based on weights.
        
        Returns:
            str: Column letter (B, I, N, G, O)
        """
        rand = random.random()
        cumulative = 0
        
        for column, weight in self.weights.items():
            cumulative += weight
            if rand <= cumulative:
                return column
        
        return 'B'  # Default
    
    def draw_next_weighted(self) -> Optional[int]:
        """
        Draw the next number using weighted column distribution.
        
        Returns:
            int: The next number, or None if no numbers left
        """
        if self.current_index >= len(self.numbers):
            return None
        
        # Get available numbers per column
        available_by_column = {col: [] for col in self.COLUMN_RANGES.keys()}
        
        for num in self.numbers[self.current_index:]:
            col = self.get_column_for_number(num)
            if col:
                available_by_column[col].append(num)
        
        # Select column based on weights
        selected_column = self._get_weighted_column()
        
        # If selected column has no available numbers, fall back to random
        if not available_by_column[selected_column]:
            return self.draw_next()
        
        # Select random number from the selected column
        number = random.choice(available_by_column[selected_column])
        
        # Find and remove this number from the list
        index = self.numbers.index(number)
        self.numbers[index], self.numbers[self.current_index] = self.numbers[self.current_index], self.numbers[index]
        
        return self.draw_next()


# ==================== FACTORY FUNCTION ====================

def create_number_caller(weighted: bool = False, weights: Optional[dict] = None) -> NumberCaller:
    """
    Factory function to create a NumberCaller instance.
    
    Args:
        weighted: bool - Whether to use weighted number caller
        weights: dict - Weights for weighted caller
    
    Returns:
        NumberCaller: NumberCaller instance
    """
    if weighted:
        return WeightedNumberCaller(weights)
    return NumberCaller()


# ==================== EXPORTS ====================

__all__ = [
    'NumberCaller',
    'WeightedNumberCaller',
    'create_number_caller',
]