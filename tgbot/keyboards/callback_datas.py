from aiogram.utils.callback_data import CallbackData

action_callback = CallbackData("action", "cur_action")
playlist_callback = CallbackData("pl_cb", "playlist_id")
edit_playlist_callback = CallbackData("ed_pl_cb", "playlist_id")
add_track_callback = CallbackData("add_track_cb", "playlist_id")
video_callback = CallbackData("video_cb", "video_id")
playlist_action = CallbackData("playlist_action", "playlist_id", "cur_action")

