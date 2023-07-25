# Global flags set by the command line arguments

config:dict[str, bool] = {
    # The following flags skip an item during the WEIGHTING step.
    "is_daily_run": False, # True if the player is in a Daily Run (exclude nodaily)
    "is_greed_mode": False, # True if the player is in Greed mode (exclude nogreed)
    "is_in_challenge": False, # True if the player is in a Challenge (exclude nochallenge)
    "has_lost_birthright": False, # True if the player has The Lost's Birthright (exclude nolostbr)
    # The following flags skip an item during the GENERATING step.
    "is_keeper": False, # True if the player is playing as Keeper (exclude nokeeper)
    "is_tlost": False, # True if the player is playing as The Lost (exclude items without offensive)
    "has_sacred_orb": False, # True if the player has Sacred Orb (exclude all items with quality 0 or 1)
    "has_trinket_no": False, # True if the player has NO! (exclude all active items)
}