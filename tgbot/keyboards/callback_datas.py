from aiogram.utils.callback_data import CallbackData

action_callback = CallbackData("action", "cur_action")
playlist_callback = CallbackData("pl_cb", "playlist_id")
add_track_callback = CallbackData("add_track_cb", "playlist_id")
video_callback = CallbackData("video_cb", "video_id")

