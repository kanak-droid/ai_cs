package com.astrolokal.astrohelp.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// The AstroLokal brand is a warm, light look — the chat webview is always
// cream, so we deliberately keep a single light scheme rather than flipping to
// a dark mode that would read as a different product.
private val BrandColors = lightColorScheme(
    primary = Terracotta,
    onPrimary = Color.White,
    primaryContainer = Terracotta100,
    onPrimaryContainer = Terracotta700,
    secondary = Terracotta700,
    onSecondary = Color.White,
    background = Cream,
    onBackground = Ink,
    surface = Surface,
    onSurface = Ink,
    surfaceVariant = Terracotta100,
    onSurfaceVariant = Muted,
    error = Clay,
    onError = Color.White,
    outline = Muted,
)

@Composable
fun AstroHelpTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = BrandColors,
        typography = Typography,
        content = content
    )
}
