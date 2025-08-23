import winsound

def play_error_sound():
    """
    Plays the Windows error sound
    """
    winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
