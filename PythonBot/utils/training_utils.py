import time

def is_player_training(user_id, training_sessions):
    """Check if a player is currently training"""
    if user_id not in training_sessions:
        return False, None
    
    session = training_sessions[user_id]
    remaining = session['end_time'] - time.time()
    
    if remaining <= 0:
        # Training completed, remove session
        del training_sessions[user_id]
        return False, None
    
    # Player is training
    minutes, seconds = divmod(int(remaining), 60)
    training_type = session['type'].title()
    return True, f"You're currently training **{training_type}**! Please wait {minutes}m {seconds}s before using other commands."

def get_training_sessions():
    """Get the training sessions from the training cog"""
    # This will be accessed through the bot instance
    return {}