"""Markdown logger for gameplay events (clicks, level-ups)."""

import datetime

class GameLogger:
    """Handles logging of game events to markdown file."""
    
    def __init__(self, log_file: str):
        """
        Initialize the game logger.
        
        Parameters
        ----------
        log_file : str
            Path to the log file
        """
        self.log_file = log_file
        self.setup_log()
    
    def setup_log(self) -> None:
        """Initialize the log file with headers."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("# Whack-a-Zombie Game Log\n\n")
                f.write(f"Log started at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("## Mouse Click Events\n\n")
                f.write("| Timestamp | Position (x,y) | Result | Details |\n")
                f.write("|-----------|---------------|--------|----------|\n")
        except Exception as e:
            print(f"Failed to initialize log file: {e}")
    
    def log_click(self, pos: tuple[int, int], hit: bool, details: str = "") -> None:
        """
        Log a mouse click event.
        
        Parameters
        ----------
        pos : Tuple[int, int]
            Mouse click position (x, y)
        hit : bool
            Whether the click hit a zombie
        details : str, optional
            Additional details about the click
        """
        try:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
            result = "HIT" if hit else "MISS"
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"| {timestamp} | ({pos[0]}, {pos[1]}) | {result} | {details} |\n")
                
        except Exception as e:
            print(f"Failed to log click: {e}")
    
    def log_level_up(self, level: int) -> None:
        """
        Log a level up event.
        
        Parameters
        ----------
        level : int
            New level reached
        """
        try:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"| {timestamp} | LEVEL UP | SYSTEM | Reached level {level} |\n")
                
        except Exception as e:
            print(f"Failed to log level up: {e}")
