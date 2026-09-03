package com.astrolokal.astrohelp

import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.astrolokal.astrohelp.ui.AppViewModel
import com.astrolokal.astrohelp.ui.CallScreen
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
        val handoffUserId =
            intent?.getStringExtra(EXTRA_USER_ID)
                ?: intent?.extras?.get(EXTRA_USER_ID)?.toString()
                ?: intent?.data?.getQueryParameter("user_id")
        val baseUrlOverride = intent?.getStringExtra(EXTRA_BASE_URL)

        setContent {
            AstroHelpTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    // Open straight to the Help & Support screen, but back it with the
                    // real AppViewModel so tapping "Receive a Call" hits the backend
                    // (POST /api/voice/request-call), which places the Twilio call.
                    val appViewModel: AppViewModel = viewModel()
                    val state by appViewModel.state.collectAsState()

                    // Authenticate once with the handed-off user_id (or saved
                    // session) so requestCall() has an authenticated ApiClient.
                    LaunchedEffect(Unit) { appViewModel.begin(handoffUserId, baseUrlOverride) }

                    CallScreen(
                        astrologerName = state.astrologer?.name.orEmpty(),
                        requesting = state.requestingCall,
                        callStatus = state.callStatus,
                        callError = state.callError,
                        onRequestCall = appViewModel::requestCall,
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
