package com.astrolokal.astrohelp.data

import android.content.Context

/** Persists the logged-in astrologer's user_id across app launches. */
class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("astrohelp_session", Context.MODE_PRIVATE)

    var userId: String?
        get() = prefs.getString(KEY_USER_ID, null)
        set(value) {
            prefs.edit().apply {
                if (value == null) remove(KEY_USER_ID) else putString(KEY_USER_ID, value)
                apply()
            }
        }

    fun clear() {
        userId = null
    }

    private companion object {
        const val KEY_USER_ID = "user_id"
    }
}
