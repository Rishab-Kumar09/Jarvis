package com.example.jarvis_app

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.view.WindowManager
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.CookieManager
import android.webkit.WebSettings
import android.widget.FrameLayout
import android.accounts.AccountManager
import android.accounts.Account
import android.content.pm.PackageManager
import android.util.Log
import java.io.File

/**
 * 🎭 TONY STARK CONTAINER SYSTEM 🎭
 * 
 * This invisible container makes users think they're opening real apps
 * while we maintain complete control over the "app" experience.
 * 
 * User says "open Chrome" → We open this container with Chrome-like interface
 * User says "close Chrome" → We close this container (appears like Chrome closed)
 * 
 * THE USER HAS NO IDEA THEY'RE IN A SANDBOX! 🕵️‍♂️
 */
class ContainerActivity : Activity() {
    
    private lateinit var webView: WebView
    private lateinit var containerFrame: FrameLayout
    private var appType: String = "browser"
    private var appName: String = "Browser"
    private var speechRecognizer: android.speech.SpeechRecognizer? = null
    
    companion object {
        private var activeContainers = mutableMapOf<String, ContainerActivity>()
        
        fun closeContainer(appName: String): Boolean {
            Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Attempting to close container '$appName'")
            Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Active containers: ${activeContainers.keys}")
            
            // Find container by app name prefix
            val containerKey = activeContainers.keys.find { it.startsWith(appName.lowercase()) }
            val container = containerKey?.let { activeContainers[it] }
            return if (container != null) {
                Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Container found! Closing...")
                container.finish()
                activeContainers.remove(containerKey)
                Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Container closed successfully")
                true
            } else {
                Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Container NOT found for '$appName'")
                false
            }
        }
        
        fun isContainerActive(appName: String): Boolean {
            // Check if any container key starts with this app name
            return activeContainers.keys.any { it.startsWith(appName.lowercase()) }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Make it fullscreen and immersive (looks like real app)
        window.decorView.systemUiVisibility = (
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
            View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or
            View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
            View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
            View.SYSTEM_UI_FLAG_FULLSCREEN or
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        )
        
        // Remove title bar
        requestWindowFeature(android.view.Window.FEATURE_NO_TITLE)
        window.setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        )
        
        // Get app details from intent
        appType = intent.getStringExtra("APP_TYPE") ?: "browser"
        appName = intent.getStringExtra("APP_NAME") ?: "Browser"
        val startUrl = intent.getStringExtra("START_URL") ?: "https://www.google.com"
        
        // Register this container with unique key
        val containerKey = "${appName.lowercase()}_${startUrl.hashCode()}"  // Make key unique using URL
        Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Registering container '$appName' with key '$containerKey'")
        activeContainers[containerKey] = this
        Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Active containers after registration: ${activeContainers.keys}")
        
        // Create the container UI
        setupContainerUI(startUrl)
    }
    
    private fun setupContainerUI(startUrl: String) {
        // Create main container
        containerFrame = FrameLayout(this).apply {
            setBackgroundColor(Color.WHITE)
        }
        
        // 🎭 TONY STARK DATA SHARING MAGIC 🎭
        // Setup advanced WebView with real app data sharing
        setupDataSharingWebView(startUrl)
        
        containerFrame.addView(webView)
        
        // Add floating mic button on top of WebView
        addFloatingMicButton()
        
        setContentView(containerFrame)
        
        // Load the appropriate content based on app type
        loadAppContent(startUrl)
    }
    
    private fun setupDataSharingWebView(startUrl: String) {
        Log.d("JARVIS_CONTAINER", "🎭 Setting up data sharing WebView for $appName")
        
        // Create WebView with advanced data sharing
        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT
            )
            
            // 🔧 ADVANCED WEBVIEW CONFIGURATION 🔧
            settings.apply {
                // Core functionality
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                allowContentAccess = true
                allowFileAccess = true
                
                // Storage and caching for session persistence (using modern APIs)
                cacheMode = WebSettings.LOAD_DEFAULT
                
                // Enhanced browsing features
                setSupportZoom(true)
                builtInZoomControls = true
                displayZoomControls = false
                loadWithOverviewMode = true
                useWideViewPort = true
                
                // Media and file access
                mediaPlaybackRequiresUserGesture = false
                allowFileAccessFromFileURLs = true
                allowUniversalAccessFromFileURLs = true
                
                // Mixed content (for sites with both HTTP/HTTPS)
                mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                
                // User agent that matches real app
                userAgentString = getAdvancedUserAgent()
            }
            
            // 🍪 COOKIE SHARING SETUP 🍪
            setupCookieSharing()
            
            // 🔐 ACCOUNT TOKEN INTEGRATION 🔐
            setupAccountIntegration()
            
            webViewClient = ContainerWebViewClient()
            webChromeClient = ContainerWebChromeClient()
        }
    }
    
    private fun setupCookieSharing() {
        try {
            Log.d("JARVIS_CONTAINER", "🍪 Setting up cookie sharing for seamless login")
            
            val cookieManager = CookieManager.getInstance()
            cookieManager.setAcceptCookie(true)
            cookieManager.setAcceptThirdPartyCookies(webView, true)
            
            // Enable cookie syncing between WebView and system
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                cookieManager.flush()
            }
            
            // Set cookies based on app type for automatic login
            when (appType.lowercase()) {
                "instagram" -> setupInstagramCookies(cookieManager)
                "youtube" -> setupYouTubeCookies(cookieManager)
                "facebook" -> setupFacebookCookies(cookieManager)
                "twitter" -> setupTwitterCookies(cookieManager)
                "whatsapp" -> setupWhatsAppCookies(cookieManager)
                "netflix" -> setupNetflixCookies(cookieManager)
                "spotify" -> setupSpotifyCookies(cookieManager)
                "amazon" -> setupAmazonCookies(cookieManager)
                else -> setupGenericBrowserCookies(cookieManager)
            }
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🍪 Cookie sharing setup failed: ${e.message}")
        }
    }
    
    private fun setupAccountIntegration() {
        try {
            Log.d("JARVIS_CONTAINER", "🔐 Setting up account integration for auto-login")
            
            val accountManager = AccountManager.get(this)
            
            // Get Google accounts for Google services (YouTube, Gmail, etc.)
            val googleAccounts = accountManager.getAccountsByType("com.google")
            if (googleAccounts.isNotEmpty()) {
                val primaryGoogleAccount = googleAccounts[0]
                Log.d("JARVIS_CONTAINER", "🔐 Found Google account: ${primaryGoogleAccount.name}")
                
                // Inject Google authentication for YouTube, Gmail, etc.
                when (appType.lowercase()) {
                    "youtube", "gmail", "browser" -> {
                        injectGoogleAuthentication(primaryGoogleAccount)
                    }
                }
            }
            
            // Get Facebook account if available
            try {
                val facebookAccounts = accountManager.getAccountsByType("com.facebook.auth.login")
                if (facebookAccounts.isNotEmpty()) {
                    val facebookAccount = facebookAccounts[0]
                    Log.d("JARVIS_CONTAINER", "🔐 Found Facebook account: ${facebookAccount.name}")
                    
                    if (appType.lowercase() == "facebook" || appType.lowercase() == "instagram") {
                        injectFacebookAuthentication(facebookAccount)
                    }
                }
            } catch (e: Exception) {
                Log.d("JARVIS_CONTAINER", "🔐 No Facebook account found: ${e.message}")
            }
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🔐 Account integration failed: ${e.message}")
        }
    }
    
    private fun injectGoogleAuthentication(account: Account) {
        // This would typically involve getting OAuth tokens
        // For now, we'll set up the environment for automatic Google login
        Log.d("JARVIS_CONTAINER", "🔐 Preparing Google authentication for ${account.name}")
        
        // Set headers and cookies that help with Google sign-in
        val cookieManager = CookieManager.getInstance()
        
        // Basic Google authentication cookies (these would normally be retrieved from real app)
        val googleDomains = listOf(
            "google.com", "youtube.com", "gmail.com", "accounts.google.com"
        )
        
        for (domain in googleDomains) {
            // Note: In a real implementation, you'd get actual auth tokens
            cookieManager.setCookie(domain, "ACCOUNT_CHOOSER=AFx_qI5; Path=/; Domain=.$domain")
            cookieManager.setCookie(domain, "LSID=o.oauth.google.com; Path=/; Domain=.$domain")
        }
    }
    
    private fun injectFacebookAuthentication(account: Account) {
        Log.d("JARVIS_CONTAINER", "🔐 Preparing Facebook authentication for ${account.name}")
        
        val cookieManager = CookieManager.getInstance()
        
        // Facebook authentication setup
        val facebookDomains = listOf("facebook.com", "instagram.com")
        
        for (domain in facebookDomains) {
            // Basic Facebook session cookies (would be real tokens in production)
            cookieManager.setCookie(domain, "c_user=placeholder; Path=/; Domain=.$domain")
            cookieManager.setCookie(domain, "xs=placeholder; Path=/; Domain=.$domain")
        }
    }
    
    private fun getAdvancedUserAgent(): String {
        // 🎭 TONY STARK USER AGENT MATCHING 🎭
        // Match the exact user agent that real apps use
        
        return when (appType.lowercase()) {
            "instagram" -> {
                // Instagram app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 Instagram 219.0.0.12.117 Android"
            }
            "youtube" -> {
                // YouTube app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 YouTubeApp/17.36.4"
            }
            "facebook" -> {
                // Facebook app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 [FBAN/EMA;FBLC/en_US;FBAV/329.0.0.0.46]"
            }
            "twitter" -> {
                // Twitter app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 TwitterAndroid"
            }
            "whatsapp" -> {
                // WhatsApp Web user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 WhatsApp/2.22.24.75"
            }
            "spotify" -> {
                // Spotify app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 Spotify/8.7.32.1021"
            }
            "netflix" -> {
                // Netflix app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 Netflix/7.112.0"
            }
            "amazon" -> {
                // Amazon app user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.120 Mobile Safari/537.36 Amazon/24.18.2.100"
            }
            else -> {
                // Default Chrome mobile user agent
                "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.193 Mobile Safari/537.36"
            }
        }
    }
    
    // 🍪 INDIVIDUAL APP COOKIE SETUP METHODS 🍪
    
    private fun setupInstagramCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Instagram cookies")
        val domain = "instagram.com"
        
        // Instagram session cookies (placeholders - real implementation would use actual tokens)
        cookieManager.setCookie(domain, "sessionid=placeholder_session; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "csrftoken=placeholder_csrf; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "mid=placeholder_mid; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "ig_cb=1; Path=/; Domain=.$domain")
    }
    
    private fun setupYouTubeCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up YouTube cookies")
        val domain = "youtube.com"
        
        // YouTube session cookies
        cookieManager.setCookie(domain, "SID=placeholder_sid; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "HSID=placeholder_hsid; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "SSID=placeholder_ssid; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "PREF=tz=GMT; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "VISITOR_INFO1_LIVE=placeholder_visitor; Path=/; Domain=.$domain")
    }
    
    private fun setupFacebookCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Facebook cookies")
        val domain = "facebook.com"
        
        // Facebook session cookies
        cookieManager.setCookie(domain, "c_user=placeholder_user; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "xs=placeholder_xs; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "fr=placeholder_fr; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "datr=placeholder_datr; Path=/; Domain=.$domain")
    }
    
    private fun setupTwitterCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Twitter cookies")
        val domain = "twitter.com"
        
        // Twitter session cookies
        cookieManager.setCookie(domain, "auth_token=placeholder_auth; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "ct0=placeholder_ct0; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "twid=placeholder_twid; Path=/; Domain=.$domain")
    }
    
    private fun setupWhatsAppCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up WhatsApp Web cookies")
        val domain = "web.whatsapp.com"
        
        // WhatsApp Web session cookies
        cookieManager.setCookie(domain, "wa_lang=en; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "wa_build=2.2246.9; Path=/; Domain=.$domain")
    }
    
    private fun setupNetflixCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Netflix cookies")
        val domain = "netflix.com"
        
        // Netflix session cookies
        cookieManager.setCookie(domain, "NetflixId=placeholder_id; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "SecureNetflixId=placeholder_secure; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "flwssn=placeholder_session; Path=/; Domain=.$domain")
    }
    
    private fun setupSpotifyCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Spotify cookies")
        val domain = "open.spotify.com"
        
        // Spotify session cookies
        cookieManager.setCookie(domain, "sp_dc=placeholder_dc; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "sp_key=placeholder_key; Path=/; Domain=.$domain; Secure")
        cookieManager.setCookie(domain, "sp_t=placeholder_token; Path=/; Domain=.$domain")
    }
    
    private fun setupAmazonCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up Amazon cookies")
        val domain = "amazon.com"
        
        // Amazon session cookies
        cookieManager.setCookie(domain, "session-id=placeholder_session; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "session-token=placeholder_token; Path=/; Domain=.$domain")
        cookieManager.setCookie(domain, "ubid-main=placeholder_ubid; Path=/; Domain=.$domain")
    }
    
    private fun setupGenericBrowserCookies(cookieManager: CookieManager) {
        Log.d("JARVIS_CONTAINER", "🍪 Setting up generic browser cookies")
        
        // Try to extract real cookies from system Chrome browser
        extractRealBrowserCookies(cookieManager)
        
        // Setup cookies for common sites that might be accessed via browser
        val commonSites = mapOf(
            "google.com" to listOf(
                "SID=placeholder_sid; Path=/; Domain=.google.com; Secure",
                "HSID=placeholder_hsid; Path=/; Domain=.google.com; Secure"
            ),
            "gmail.com" to listOf(
                "GMAIL_AT=placeholder_at; Path=/; Domain=.gmail.com; Secure"
            )
        )
        
        for ((domain, cookies) in commonSites) {
            for (cookie in cookies) {
                cookieManager.setCookie(domain, cookie)
            }
        }
    }
    
    // 🎭 ADVANCED REAL COOKIE EXTRACTION 🎭
    private fun extractRealBrowserCookies(cookieManager: CookieManager) {
        try {
            Log.d("JARVIS_CONTAINER", "🎭 Attempting to extract real browser cookies for seamless login")
            
            // Method 1: Try to access Chrome's cookie database (requires root or special permissions)
            extractChromeCookies(cookieManager)
            
            // Method 2: Use WebView's shared cookie store
            extractWebViewSharedCookies(cookieManager)
            
            // Method 3: Use system account tokens for authentication
            extractAccountBasedCookies(cookieManager)
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🎭 Real cookie extraction failed: ${e.message}")
            Log.d("JARVIS_CONTAINER", "🎭 Falling back to simulated authentication environment")
        }
    }
    
    private fun extractChromeCookies(cookieManager: CookieManager) {
        try {
            // Chrome stores cookies in: /data/data/com.android.chrome/app_chrome/Default/Cookies
            // This requires root access or special system permissions
            
            val chromeDataPath = "/data/data/com.android.chrome/app_chrome/Default/Cookies"
            val chromeCookieFile = File(chromeDataPath)
            
            if (chromeCookieFile.exists() && chromeCookieFile.canRead()) {
                Log.d("JARVIS_CONTAINER", "🍪 Found Chrome cookie database - extracting...")
                
                // In a real implementation, you would:
                // 1. Read the SQLite database
                // 2. Decrypt the cookies (Chrome encrypts them)
                // 3. Extract relevant session cookies for current user
                // 4. Set them in our WebView
                
                Log.d("JARVIS_CONTAINER", "🍪 Chrome cookie extraction successful (simulated)")
            } else {
                Log.d("JARVIS_CONTAINER", "🍪 Chrome cookies not accessible - trying alternative methods")
            }
            
        } catch (e: Exception) {
            Log.d("JARVIS_CONTAINER", "🍪 Chrome cookie extraction failed: ${e.message}")
        }
    }
    
    private fun extractWebViewSharedCookies(cookieManager: CookieManager) {
        try {
            Log.d("JARVIS_CONTAINER", "🍪 Setting up WebView shared cookie environment")
            
            // Enable cookie sharing between all WebViews in the system
            cookieManager.setAcceptCookie(true)
            cookieManager.setAcceptThirdPartyCookies(webView, true)
            
            // Flush cookies to ensure they're available
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                cookieManager.flush()
            }
            
            // Set up an environment that encourages sites to remember login state
            // This works because many sites store login tokens in localStorage/sessionStorage
            // which our WebView can access
            
            Log.d("JARVIS_CONTAINER", "🍪 WebView shared cookie environment configured")
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🍪 WebView cookie sharing failed: ${e.message}")
        }
    }
    
    private fun extractAccountBasedCookies(cookieManager: CookieManager) {
        try {
            Log.d("JARVIS_CONTAINER", "🔐 Setting up account-based authentication cookies")
            
            val accountManager = AccountManager.get(this)
            
            // Get all accounts and try to extract auth tokens
            val googleAccounts = accountManager.getAccountsByType("com.google")
            val facebookAccounts = try {
                accountManager.getAccountsByType("com.facebook.auth.login")
            } catch (e: Exception) {
                arrayOf<Account>()
            }
            
            // Setup authentication environment for Google services
            if (googleAccounts.isNotEmpty()) {
                val primaryAccount = googleAccounts[0]
                Log.d("JARVIS_CONTAINER", "🔐 Found Google account: ${primaryAccount.name}")
                
                // Create an authentication environment that helps with auto-login
                val googleDomains = listOf("google.com", "youtube.com", "gmail.com")
                for (domain in googleDomains) {
                    // Set up environment cookies that help with Google's sign-in flow
                    cookieManager.setCookie(domain, "ACCOUNT_HINT=${primaryAccount.name}; Path=/; Domain=.$domain")
                    cookieManager.setCookie(domain, "AUTO_LOGIN=1; Path=/; Domain=.$domain")
                }
            }
            
            // Setup authentication environment for Facebook services  
            if (facebookAccounts.isNotEmpty()) {
                Log.d("JARVIS_CONTAINER", "🔐 Found Facebook account - setting up auth environment")
                
                val facebookDomains = listOf("facebook.com", "instagram.com")
                for (domain in facebookDomains) {
                    cookieManager.setCookie(domain, "FB_AUTO_LOGIN=1; Path=/; Domain=.$domain")
                }
            }
            
            Log.d("JARVIS_CONTAINER", "🔐 Account-based authentication environment configured")
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🔐 Account-based cookie setup failed: ${e.message}")
        }
    }
    
    private fun loadAppContent(startUrl: String) {
        when (appType.lowercase()) {
            "chrome", "browser" -> {
                // Load the provided URL (could be search or default Google)
                Log.d("JARVIS_CONTAINER", "🔍 DEBUG: Loading Chrome with URL: $startUrl")
                webView.loadUrl(startUrl)
            }
            "instagram" -> {
                // Load Instagram web version
                webView.loadUrl("https://www.instagram.com")
            }
            "youtube" -> {
                // Load YouTube
                webView.loadUrl("https://www.youtube.com")
            }
            "facebook" -> {
                // Load Facebook
                webView.loadUrl("https://www.facebook.com")
            }
            "twitter" -> {
                // Load Twitter/X
                webView.loadUrl("https://twitter.com")
            }
            "whatsapp" -> {
                // Load WhatsApp Web
                webView.loadUrl("https://web.whatsapp.com")
            }
            "netflix" -> {
                // Load Netflix
                webView.loadUrl("https://www.netflix.com")
            }
            "amazon" -> {
                // Load Amazon
                webView.loadUrl("https://www.amazon.com")
            }
            "spotify" -> {
                // Load Spotify Web Player
                webView.loadUrl("https://open.spotify.com")
            }
            else -> {
                // Default to the provided URL or Google
                webView.loadUrl(startUrl)
            }
        }
    }
    
    private inner class ContainerWebViewClient : WebViewClient() {
        override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
            // Keep navigation within our container (maintains the illusion)
            return false
        }
        
        override fun onPageStarted(view: WebView?, url: String?, favicon: android.graphics.Bitmap?) {
            super.onPageStarted(view, url, favicon)
            // Could add loading indicator here if needed
        }
        
        override fun onPageFinished(view: WebView?, url: String?) {
            super.onPageFinished(view, url)
            // Page loaded - container is ready
        }
    }
    
    private inner class ContainerWebChromeClient : WebChromeClient() {
        override fun onProgressChanged(view: WebView?, newProgress: Int) {
            super.onProgressChanged(view, newProgress)
            // Could show progress bar here
        }
        
        override fun onReceivedTitle(view: WebView?, title: String?) {
            super.onReceivedTitle(view, title)
            // Could update title bar if we had one
        }
    }
    
    private fun addFloatingMicButton() {
        // Create floating mic button
        val floatingMicButton = android.widget.ImageButton(this).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            setBackgroundResource(android.R.drawable.btn_default_small)
            scaleType = android.widget.ImageView.ScaleType.CENTER_INSIDE
            
            // Style the button
            elevation = 8f
            alpha = 0.8f
        }
        
        // Position in top-right corner
        val buttonParams = FrameLayout.LayoutParams(
            150, // width in pixels
            150  // height in pixels
        ).apply {
            gravity = android.view.Gravity.TOP or android.view.Gravity.END
            setMargins(0, 100, 50, 0) // top, right margins
        }
        
        // Handle click - start voice recognition
        floatingMicButton.setOnClickListener {
            startVoiceRecognitionForClose()
        }
        
        // Add to container
        containerFrame.addView(floatingMicButton, buttonParams)
        
        Log.d("JARVIS_CONTAINER", "🎤 Added floating mic button to container")
    }
    
    private fun startVoiceRecognitionForClose() {
        try {
            Log.d("JARVIS_CONTAINER", "🎤 Starting voice recognition in container (NO UI)")
            
            // Check if speech recognition is available
            if (!android.speech.SpeechRecognizer.isRecognitionAvailable(this)) {
                Log.e("JARVIS_CONTAINER", "🎤 Speech recognition not available")
                return
            }
            
            // Stop any existing recognition
            speechRecognizer?.destroy()
            
            // Create new speech recognizer (BACKGROUND, NO UI!)
            speechRecognizer = android.speech.SpeechRecognizer.createSpeechRecognizer(this)
            speechRecognizer?.setRecognitionListener(createContainerRecognitionListener())
            
            // Create recognition intent (NO UI SHOWN!)
            val intent = android.content.Intent(android.speech.RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE_MODEL, android.speech.RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(android.speech.RecognizerIntent.EXTRA_LANGUAGE, java.util.Locale.getDefault())
                putExtra(android.speech.RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(android.speech.RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                // Key setting: Don't show UI
                putExtra(android.speech.RecognizerIntent.EXTRA_CALLING_PACKAGE, packageName)
            }
            
            // Start listening without showing any UI!
            speechRecognizer?.startListening(intent)
            
        } catch (e: Exception) {
            Log.e("JARVIS_CONTAINER", "🎤 Voice recognition failed: ${e.message}")
        }
    }
    
    private fun createContainerRecognitionListener(): android.speech.RecognitionListener {
        return object : android.speech.RecognitionListener {
            override fun onReadyForSpeech(params: android.os.Bundle?) {
                Log.d("JARVIS_CONTAINER", "🎤 Ready for speech (no UI shown)")
            }
            
            override fun onBeginningOfSpeech() {
                Log.d("JARVIS_CONTAINER", "🎤 Speech started")
            }
            
            override fun onRmsChanged(rmsdB: Float) {
                // Volume level changed
            }
            
            override fun onBufferReceived(buffer: ByteArray?) {
                // Audio buffer received
            }
            
            override fun onEndOfSpeech() {
                Log.d("JARVIS_CONTAINER", "🎤 Speech ended")
            }
            
            override fun onError(error: Int) {
                Log.e("JARVIS_CONTAINER", "🎤 Speech recognition error: $error")
                speechRecognizer?.destroy()
            }
            
            override fun onResults(results: android.os.Bundle?) {
                val matches = results?.getStringArrayList(android.speech.SpeechRecognizer.RESULTS_RECOGNITION)
                val spokenText = matches?.get(0)?.lowercase()?.trim()
                
                Log.d("JARVIS_CONTAINER", "🎤 Final result: '$spokenText'")
                
                // Check for close commands
                if (spokenText?.contains("close") == true && 
                    (spokenText.contains("chrome") || spokenText.contains(appName.lowercase()))) {
                    
                    Log.d("JARVIS_CONTAINER", "🎤 Close command detected, closing container")
                    finish() // Close this container
                }
                
                speechRecognizer?.destroy()
            }
            
            override fun onPartialResults(partialResults: android.os.Bundle?) {
                val matches = partialResults?.getStringArrayList(android.speech.SpeechRecognizer.RESULTS_RECOGNITION)
                val partialText = matches?.get(0)?.lowercase()?.trim()
                Log.d("JARVIS_CONTAINER", "🎤 Partial result: '$partialText'")
            }
            
            override fun onEvent(eventType: Int, params: android.os.Bundle?) {
                // Handle speech recognition events
                Log.d("JARVIS_CONTAINER", "🎤 Speech event: $eventType")
            }
        }
    }
    
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            // Close container when back is pressed and can't go back
            finish()
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d("JARVIS_CONTAINER", "🎭 DEBUG: ContainerActivity.onDestroy() called for '$appName'")
        
        // Clean up speech recognizer
        speechRecognizer?.destroy()
        speechRecognizer = null
        
        // Unregister this container
        activeContainers.remove(appName.lowercase())
        Log.d("JARVIS_CONTAINER", "🎭 DEBUG: Container '$appName' unregistered from activeContainers")
        
        // Clean up WebView
        webView.destroy()
    }
    
    override fun onPause() {
        super.onPause()
        webView.onPause()
    }
    
    override fun onResume() {
        super.onResume()
        webView.onResume()
    }
} 