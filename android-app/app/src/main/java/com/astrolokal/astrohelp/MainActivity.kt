package com.astrolokal.astrohelp

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.astrolokal.astrohelp.ui.theme.AstroHelpTheme

/**
 * Wrapper entry point for AstroHelp.
 *
 * The existing AstroLokal app (where astrologers and users connect) launches
 * this Activity directly, handing off the already-authenticated astrologer's
 * user_id — no in-app login needed. See [start] for the one-line launch helper.
 *
 * When launched with no user_id (running this module standalone, or in dev),
 * it falls back to a saved session, then to the login screen.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Accept the handoff as a String or a numeric extra, and also as a
        // deep-link query param (astrohelp://open?user_id=123) for flexibility.
        val baseUrlOverride = intent?.getStringExtra(EXTRA_BASE_URL)

        setContent {
            AstroHelpTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    // TEMP preview harness — renders the Help & Support screen directly
                    // so the UI can be viewed without a running backend. Revert to
                    // AstroHelpApp(...) after review.
                    com.astrolokal.astrohelp.ui.CallScreen(
                        astrologerName = "Priya",
                        requesting = false,
                        callStatus = null,
                        callError = null,
                        onRequestCall = {},
                    )
                }
            }
        }
    }

    companion object {
        const val EXTRA_USER_ID = "user_id"
        const val EXTRA_BASE_URL = "base_url"

        /**
         * Launch AstroHelp from the host app:
         * ```
         * MainActivity.start(context, astrologerUserId = 12345)
         * ```
         */
        fun start(context: Context, astrologerUserId: Long, baseUrl: String? = null) {
            val intent = Intent(context, MainActivity::class.java).apply {
                putExtra(EXTRA_USER_ID, astrologerUserId.toString())
                if (baseUrl != null) putExtra(EXTRA_BASE_URL, baseUrl)
            }
            context.startActivity(intent)
        }
    }
}
