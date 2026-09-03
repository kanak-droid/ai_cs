package com.astrolokal.astrohelp.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.LowPriority
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PriorityHigh
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.astrolokal.astrohelp.ui.theme.AstroHelpTheme
import com.astrolokal.astrohelp.ui.theme.Clay
import com.astrolokal.astrohelp.ui.theme.Moss
import com.astrolokal.astrohelp.ui.theme.Ochre

/** Which queue the backend should place the callback in. UI-level selection only. */
enum class CallPriority { HIGH, LOW }

@Composable
fun CallScreen(
    astrologerName: String,
    requesting: Boolean,
    callStatus: String?,
    callError: String?,
    onRequestCall: () -> Unit,
) {
    val scheme = MaterialTheme.colorScheme
    var priority by remember { mutableStateOf(CallPriority.HIGH) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(scheme.background)
            .windowInsetsPadding(WindowInsets.systemBars)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
       /* DevOnlyBadge()*/

        Spacer(Modifier.height(12.dp))

        Text(
            "Help & Support",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.SemiBold,
            color = scheme.onBackground,
        )
        Text(
            "We're here whenever you need a hand.",
            style = MaterialTheme.typography.bodyMedium,
            color = scheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 4.dp),
        )

        Spacer(Modifier.height(16.dp))

        // Priority selector — tells the backend which queue to place the call in.
       /* Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            PriorityOption(
                modifier = Modifier.weight(1f),
                icon = Icons.Filled.PriorityHigh,
                title = "High priority",
                subtitle = "Urgent · call first",
                accent = Clay,
                selected = priority == CallPriority.HIGH,
                onClick = { priority = CallPriority.HIGH },
            )
            PriorityOption(
                modifier = Modifier.weight(1f),
                icon = Icons.Filled.LowPriority,
                title = "Low priority",
                subtitle = "Can wait a bit",
                accent = Ochre,
                selected = priority == CallPriority.LOW,
                onClick = { priority = CallPriority.LOW },
            )
        }*/

        Spacer(Modifier.weight(1f))

        ReceiveCallCard(
            requesting = requesting,
            confirmed = callStatus != null,
            onRequestCall = onRequestCall,
        )

        Spacer(Modifier.weight(1f))

        if (callStatus != null) {
            Spacer(Modifier.height(12.dp))
            StatusBanner(
                icon = Icons.Filled.CheckCircle,
                tint = Moss,
                title = "Your call is on its way",
                message = "AstroHelp will ring your registered number shortly.",
            )
        }

        if (callError != null) {
            Spacer(Modifier.height(12.dp))
            StatusBanner(
                icon = Icons.Filled.Call,
                tint = scheme.error,
                title = "Couldn't place the call",
                message = callError,
            )
        }

        Spacer(Modifier.height(28.dp))

        /*Text(
            "What we can help with",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
            color = scheme.onBackground,
            modifier = Modifier.padding(bottom = 12.dp),
        )*/

       /* HelpTopicRow(Icons.Filled.Payments, "Payouts & earnings", "Track, delays and corrections")
        HelpTopicRow(Icons.Filled.VerifiedUser, "KYC & verification", "Documents and account status")
        HelpTopicRow(Icons.Filled.ReceiptLong, "Salary & invoices", "Statements and breakdowns")
        HelpTopicRow(Icons.Filled.Person, "Account & profile", "Details, access and settings")*/
    }
}

/**
 * The hero "Receive a Call" panel — a warm gradient card that makes the primary
 * action unmistakable while staying inside the AstroLokal brand.
 */
@Composable
private fun ReceiveCallCard(
    requesting: Boolean,
    confirmed: Boolean,
    onRequestCall: () -> Unit,
) {
    val scheme = MaterialTheme.colorScheme

    Surface(
        shape = RoundedCornerShape(24.dp),
        color = scheme.surface,
        tonalElevation = 0.dp,
        shadowElevation = 2.dp,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier
                .background(
                    Brush.verticalGradient(
                        listOf(scheme.primaryContainer, scheme.surface),
                    ),
                )
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .background(scheme.primary, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.Call,
                    contentDescription = null,
                    tint = scheme.onPrimary,
                    modifier = Modifier.size(38.dp),
                )
            }

            Text(
                "Receive a Call",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = scheme.onBackground,
                modifier = Modifier.padding(top = 16.dp),
            )
            Text(
                "Request a callback and our AstroHelp assistant will call you on your registered number.",
                style = MaterialTheme.typography.bodyMedium,
                color = scheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 6.dp, start = 4.dp, end = 4.dp),
            )

            Spacer(Modifier.height(12.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    Icons.Filled.Bolt,
                    contentDescription = null,
                    tint = scheme.primary,
                    modifier = Modifier.size(16.dp),
                )
                Text(
                    "Instant callback",
                    style = MaterialTheme.typography.labelMedium,
                    color = scheme.primary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(start = 6.dp),
                )
            }

            Spacer(Modifier.height(20.dp))

            Button(
                onClick = onRequestCall,
                enabled = !requesting,
                shape = RoundedCornerShape(50),
                contentPadding = PaddingValues(horizontal = 36.dp, vertical = 14.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = scheme.primary,
                    contentColor = scheme.onPrimary,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (requesting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                        color = scheme.onPrimary,
                    )
                    Spacer(Modifier.size(8.dp))
                    Text("Requesting…", fontWeight = FontWeight.SemiBold)
                } else {
                    Icon(Icons.Filled.Call, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.size(8.dp))
                    Text(
                        if (confirmed) "Call me again" else "Receive a Call",
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
        }
    }
}

/**
 * A small, tappable priority tile. Selected state is shown with the accent color
 * as a filled tint + border so it's obvious which queue the call will use.
 */
@Composable
private fun PriorityOption(
    icon: ImageVector,
    title: String,
    subtitle: String,
    accent: Color,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val scheme = MaterialTheme.colorScheme
    val container = if (selected) accent.copy(alpha = 0.12f) else scheme.surface
    val border = if (selected) accent else scheme.outline.copy(alpha = 0.25f)
    val contentColor = if (selected) accent else scheme.onSurfaceVariant

    Surface(
        shape = RoundedCornerShape(14.dp),
        color = container,
        border = BorderStroke(if (selected) 1.5.dp else 1.dp, border),
        modifier = modifier.clickable(onClick = onClick),
    ) {
        Column(
            modifier = Modifier.padding(vertical = 12.dp, horizontal = 10.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Icon(
                icon,
                contentDescription = null,
                tint = contentColor,
                modifier = Modifier.size(20.dp),
            )
            Text(
                title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                color = if (selected) accent else scheme.onBackground,
                modifier = Modifier.padding(top = 6.dp),
            )
            Text(
                subtitle,
                style = MaterialTheme.typography.labelSmall,
                color = scheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 2.dp),
            )
        }
    }
}

/** A conspicuous pill marking this screen as internal / dev-only. */
@Composable
private fun DevOnlyBadge() {
    Surface(
        shape = RoundedCornerShape(50),
        color = Ochre.copy(alpha = 0.15f),
        border = BorderStroke(1.dp, Ochre.copy(alpha = 0.5f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(
                Icons.Filled.Build,
                contentDescription = null,
                tint = Ochre,
                modifier = Modifier.size(14.dp),
            )
            Text(
                "Dev only · internal testing",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.SemiBold,
                color = Ochre,
                modifier = Modifier.padding(start = 6.dp),
            )
        }
    }
}

@Composable
private fun HelpTopicRow(icon: ImageVector, title: String, subtitle: String) {
    val scheme = MaterialTheme.colorScheme

    Surface(
        shape = RoundedCornerShape(16.dp),
        color = scheme.surface,
        shadowElevation = 1.dp,
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 10.dp),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(40.dp)
                    .background(scheme.primaryContainer, RoundedCornerShape(12.dp)),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    icon,
                    contentDescription = null,
                    tint = scheme.primary,
                    modifier = Modifier.size(20.dp),
                )
            }
            Column(modifier = Modifier.padding(start = 14.dp)) {
                Text(
                    title,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                    color = scheme.onBackground,
                )
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = scheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun StatusBanner(icon: ImageVector, tint: Color, title: String, message: String) {
    Surface(
        shape = RoundedCornerShape(16.dp),
        color = tint.copy(alpha = 0.10f),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(22.dp))
            Column(modifier = Modifier.padding(start = 12.dp)) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = tint,
                )
                Text(
                    message,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun CallScreenPreview() {
    AstroHelpTheme {
        CallScreen(
            astrologerName = "Priya",
            requesting = false,
            callStatus = null,
            callError = null,
            onRequestCall = {},
        )
    }
}
