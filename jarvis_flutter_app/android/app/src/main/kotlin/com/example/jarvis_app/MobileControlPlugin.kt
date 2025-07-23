package com.example.jarvis_app

import android.app.Activity
import android.app.ActivityManager
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.database.Cursor
import android.hardware.camera2.CameraAccessException
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.provider.ContactsContract
import android.provider.Settings
import android.widget.Toast
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.MethodChannel.MethodCallHandler
import io.flutter.plugin.common.MethodChannel.Result
import android.content.Context
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import android.Manifest
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.RecognitionListener
import android.os.Bundle
import java.util.Locale
import android.telephony.SmsManager
import android.util.Log

class MobileControlPlugin(private val activity: Activity) : MethodCallHandler {
    
    private var speechRecognitionResult: Result? = null
    private val SPEECH_REQUEST_CODE = 1001
    private var speechRecognizer: SpeechRecognizer? = null
    
    // Always listening variables
    private var isAlwaysListening = false
    private var methodChannel: MethodChannel? = null
    
    companion object {
        private const val CHANNEL_NAME = "jarvis_mobile_control"
    }
    
    private var flashlightOn = false
    
    fun register(flutterEngine: FlutterEngine) {
        val channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL_NAME)
        methodChannel = channel
        channel.setMethodCallHandler(this)
    }
    
    override fun onMethodCall(call: MethodCall, result: Result) {
        when (call.method) {
            "launchApp" -> {
                val packageName = call.argument<String>("packageName")
                if (packageName != null) {
                    launchAppOrContainer(packageName, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Package name is required", null)
                }
            }
            "openContainer" -> {
                val appName = call.argument<String>("appName")
                val appType = call.argument<String>("appType") ?: "browser"
                val startUrl = call.argument<String>("startUrl") ?: "https://www.google.com"
                if (appName != null) {
                    openContainer(appName, appType, startUrl, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "App name is required", null)
                }
            }
            "closeContainer" -> {
                val appName = call.argument<String>("appName")
                if (appName != null) {
                    closeContainer(appName, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "App name is required", null)
                }
            }
            "openSettings" -> {
                val action = call.argument<String>("action") ?: Settings.ACTION_SETTINGS
                openSettings(action, result)
            }
            "createNote" -> {
                val content = call.argument<String>("content")
                if (content != null) {
                    createNote(content, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Note content is required", null)
                }
            }
            "volumeUp" -> {
                adjustVolume(AudioManager.ADJUST_RAISE, result)
            }
            "volumeDown" -> {
                adjustVolume(AudioManager.ADJUST_LOWER, result)
            }
            "volumeMute" -> {
                adjustVolume(AudioManager.ADJUST_MUTE, result)
            }
            "flashlightOn" -> {
                toggleFlashlight(true, result)
            }
            "flashlightOff" -> {
                toggleFlashlight(false, result)
            }
            "closeApp" -> {
                val packageName = call.argument<String>("packageName")
                if (packageName != null) {
                    closeApp(packageName, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Package name is required", null)
                }
            }
            "getContacts" -> {
                getContacts(result)
            }
            "findContact" -> {
                val contactName = call.argument<String>("contactName")
                if (contactName != null) {
                    findContactByName(contactName, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Contact name is required", null)
                }
            }
            "callContact" -> {
                val contactName = call.argument<String>("contactName")
                if (contactName != null) {
                    callContactByName(contactName, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Contact name is required", null)
                }
            }
            "sendSMSDirect" -> {
                val phoneNumber = call.argument<String>("phoneNumber")
                val message = call.argument<String>("message")
                if (phoneNumber != null && message != null) {
                    sendSMSDirect(phoneNumber, message, result)
                } else {
                    result.error("INVALID_ARGUMENTS", "Phone number and message are required", null)
                }
            }
            "startVoiceRecognition" -> {
                startVoiceRecognition(result)
            }
            "startAlwaysListen" -> {
                startAlwaysListen(result)
            }
            "stopAlwaysListen" -> {
                stopAlwaysListen(result)
            }
            else -> {
                result.notImplemented()
            }
        }
    }
    
    private fun openSettings(action: String, result: Result) {
        try {
            val intent = Intent(action)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            activity.startActivity(intent)
            result.success("Settings opened successfully")
        } catch (e: Exception) {
            result.error("SETTINGS_ERROR", "Failed to open settings: ${e.message}", null)
        }
    }
    
    private fun createNote(content: String, result: Result) {
        try {
            // Try Samsung Notes first
            var intent = Intent().apply {
                setPackage("com.samsung.android.app.notes")
                action = Intent.ACTION_SEND
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, content)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            
            try {
                activity.startActivity(intent)
                result.success("Note created in Samsung Notes")
                return
            } catch (e: Exception) {
                // Samsung Notes not available, try generic note intent
            }
            
            // Fallback to generic note creation
            intent = Intent().apply {
                action = Intent.ACTION_SEND
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, content)
                putExtra(Intent.EXTRA_SUBJECT, "JARVIS Note")
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            
            val chooser = Intent.createChooser(intent, "Create Note")
            chooser.flags = Intent.FLAG_ACTIVITY_NEW_TASK
            activity.startActivity(chooser)
            result.success("Note creation app opened")
            
        } catch (e: Exception) {
            result.error("NOTE_ERROR", "Failed to create note: ${e.message}", null)
        }
    }
    
    private fun adjustVolume(direction: Int, result: Result) {
        try {
            val audioManager = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            audioManager.adjustStreamVolume(
                AudioManager.STREAM_MUSIC,
                direction,
                AudioManager.FLAG_SHOW_UI
            )
            
            val volumeDesc = when (direction) {
                AudioManager.ADJUST_RAISE -> "increased"
                AudioManager.ADJUST_LOWER -> "decreased"
                AudioManager.ADJUST_MUTE -> "muted"
                else -> "adjusted"
            }
            
            result.success("Volume $volumeDesc")
        } catch (e: Exception) {
            result.error("VOLUME_ERROR", "Failed to adjust volume: ${e.message}", null)
        }
    }
    
    private fun toggleFlashlight(turnOn: Boolean, result: Result) {
        try {
            val cameraManager = activity.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val cameraIds = cameraManager.cameraIdList
            
            if (cameraIds.isNotEmpty()) {
                val cameraId = cameraIds[0] // Usually back camera
                cameraManager.setTorchMode(cameraId, turnOn)
                flashlightOn = turnOn
                
                val status = if (turnOn) "turned on" else "turned off"
                result.success("Flashlight $status")
            } else {
                result.error("NO_CAMERA", "No camera available for flashlight", null)
            }
        } catch (e: CameraAccessException) {
            result.error("CAMERA_ERROR", "Camera access error: ${e.message}", null)
        } catch (e: Exception) {
            result.error("FLASHLIGHT_ERROR", "Flashlight error: ${e.message}", null)
        }
    }
    
    private fun closeApp(packageName: String, result: Result) {
        // 🎭 TONY STARK MAGIC: Try to close container first (invisible to user!)
        val appName = getAppNameFromPackage(packageName)
        if (ContainerActivity.isContainerActive(appName)) {
            val success = ContainerActivity.closeContainer(appName)
            if (success) {
                // Bring JARVIS back to foreground for seamless experience
                bringJarvisToForeground()
                result.success("✅ Closed $appName (container closed seamlessly)")
                return
            }
        }
        
        // Fallback: Handle real apps (existing logic)
        try {
            val activityManager = activity.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
            
            // Method 1: Kill background processes first
            var killedBackground = false
            try {
                activityManager.killBackgroundProcesses(packageName)
                killedBackground = true
            } catch (e: Exception) {
                // Ignore if this fails
            }
            
            // Method 2: For newer Android versions, try to remove from recent tasks
            try {
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.LOLLIPOP) {
                    val recentTasks = activityManager.getRecentTasks(20, ActivityManager.RECENT_IGNORE_UNAVAILABLE)
                    for (taskInfo in recentTasks) {
                        if (taskInfo.baseIntent?.component?.packageName == packageName) {
                            // Found the task, try to finish it
                            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                                // On newer versions, we can't directly finish tasks, so we'll send it to background
                                val intent = Intent().apply {
                                    component = taskInfo.baseIntent?.component
                                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
                                    action = Intent.ACTION_MAIN
                                    addCategory(Intent.CATEGORY_LAUNCHER)
                                }
                                
                                // Launch the app briefly
                                activity.startActivity(intent)
                                
                                // Immediately bring JARVIS back to foreground
                                Thread.sleep(100)
                                bringJarvisToForeground()
                                
                                result.success("✅ Closed $packageName (minimized to background)")
                                return
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                // Continue to next method
            }
            
            // Method 3: Direct approach - launch and immediately background
            try {
                val launchIntent = activity.packageManager.getLaunchIntentForPackage(packageName)
                if (launchIntent != null) {
                    // Launch the target app
                    launchIntent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                    activity.startActivity(launchIntent)
                    
                    // Immediately bring JARVIS back to foreground (this backgrounds the target app)
                    Thread.sleep(100)
                    bringJarvisToForeground()
                    
                    result.success("✅ Closed $packageName (sent to background)")
                } else {
                    if (killedBackground) {
                        result.success("✅ Closed $packageName (background processes killed)")
                    } else {
                        result.success("✅ App $packageName was not found or not running")
                    }
                }
            } catch (e: Exception) {
                if (killedBackground) {
                    result.success("✅ Closed $packageName (background processes killed)")
                } else {
                    result.error("CLOSE_APP_ERROR", "Could not close $packageName: ${e.message}", null)
                }
            }
            
        } catch (e: Exception) {
            result.error("CLOSE_APP_ERROR", "Failed to close app: ${e.message}", null)
        }
    }
    
    private fun getContacts(result: Result) {
        if (ContextCompat.checkSelfPermission(activity, Manifest.permission.READ_CONTACTS) 
            != PackageManager.PERMISSION_GRANTED) {
            result.error("PERMISSION_DENIED", "Contacts permission not granted", null)
            return
        }
        
        try {
            val contacts = mutableListOf<Map<String, String>>()
            val cursor: Cursor? = activity.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                ),
                null, null,
                ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME + " ASC"
            )
            
            cursor?.use {
                val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                
                while (it.moveToNext()) {
                    val name = it.getString(nameIndex) ?: "Unknown"
                    val number = it.getString(numberIndex) ?: "Unknown"
                    
                    contacts.add(mapOf(
                        "name" to name,
                        "phone" to number
                    ))
                }
            }
            
            result.success(contacts.take(50)) // Limit to 50 contacts for performance
        } catch (e: Exception) {
            result.error("CONTACTS_ERROR", "Failed to get contacts: ${e.message}", null)
        }
    }
    
    private fun findContactByName(contactName: String, result: Result) {
        if (ContextCompat.checkSelfPermission(activity, Manifest.permission.READ_CONTACTS) 
            != PackageManager.PERMISSION_GRANTED) {
            result.error("PERMISSION_DENIED", "Contacts permission not granted", null)
            return
        }
        
        try {
            // Get all contacts first for smart fuzzy matching
            val allContacts = mutableListOf<ContactInfo>()
            
            val cursor: Cursor? = activity.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                ),
                null,
                null,
                null
            )
            
            cursor?.use {
                val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                
                while (it.moveToNext()) {
                    val name = it.getString(nameIndex)
                    val number = it.getString(numberIndex)
                    if (name != null && number != null) {
                        allContacts.add(ContactInfo(name, number))
                    }
                }
            }
            
            // Find best match using fuzzy matching
            val bestMatch = findBestContactMatch(contactName, allContacts)
            
            if (bestMatch != null) {
                result.success(mapOf(
                    "name" to bestMatch.name,
                    "phone" to bestMatch.number,
                    "found" to true,
                    "confidence" to bestMatch.confidence
                ))
            } else {
                result.success(mapOf(
                    "found" to false,
                    "message" to "No close match found for '$contactName'. Try being more specific."
                ))
            }
        } catch (e: Exception) {
            result.error("CONTACT_SEARCH_ERROR", "Failed to search contact: ${e.message}", null)
        }
    }
    
    private data class ContactInfo(val name: String, val number: String, val confidence: Double = 0.0)
    
    private fun findBestContactMatch(searchName: String, contacts: List<ContactInfo>): ContactInfo? {
        val normalizedSearch = normalizeContactName(searchName)
        var bestMatch: ContactInfo? = null
        var bestScore = 0.0
        
        // Debug logging
        println("🔍 JARVIS DEBUG: Searching for '$searchName' (normalized: '$normalizedSearch')")
        println("🔍 JARVIS DEBUG: Found ${contacts.size} contacts to search through")
        
        for (contact in contacts) {
            val normalizedContact = normalizeContactName(contact.name)
            
            // Calculate similarity score using multiple methods
            val exactScore = if (normalizedContact.contains(normalizedSearch) || 
                                normalizedSearch.contains(normalizedContact)) 1.0 else 0.0
            
            val fuzzyScore = calculateFuzzyScore(normalizedSearch, normalizedContact)
            val phoneticScore = calculatePhoneticScore(normalizedSearch, normalizedContact)
            
            // Weighted combination of scores (prioritize fuzzy/phonetic for better matching)
            val finalScore = (exactScore * 0.2) + (fuzzyScore * 0.6) + (phoneticScore * 0.2)
            
            // Debug logging for high scores
            if (finalScore > 0.3) {
                println("🔍 JARVIS DEBUG: '${contact.name}' -> exact:$exactScore, fuzzy:$fuzzyScore, phonetic:$phoneticScore, final:$finalScore")
            }
            
            if (finalScore > bestScore && finalScore > 0.4) { // 40% confidence threshold (optimized for speech recognition)
                bestScore = finalScore
                bestMatch = ContactInfo(contact.name, contact.number, finalScore)
            }
        }
        
        if (bestMatch != null) {
            println("🔍 JARVIS DEBUG: Best match found: '${bestMatch.name}' with ${(bestMatch.confidence * 100).toInt()}% confidence")
        } else {
            println("🔍 JARVIS DEBUG: No match found above 40% threshold. Best score was: $bestScore")
        }
        
        return bestMatch
    }
    
    private fun normalizeContactName(name: String): String {
        return name.lowercase()
            .replace(Regex("[^a-z0-9\\s]"), "") // Remove special characters
            .replace(Regex("\\s+"), " ")        // Normalize spaces
            .trim()
    }
    
    private fun calculateFuzzyScore(str1: String, str2: String): Double {
        val maxLen = maxOf(str1.length, str2.length)
        if (maxLen == 0) return 1.0
        
        val distance = levenshteinDistance(str1, str2)
        return 1.0 - (distance.toDouble() / maxLen)
    }
    
    private fun calculatePhoneticScore(str1: String, str2: String): Double {
        // Handle common phonetic variations
        val phoneticVariations = mapOf(
            "mummy" to listOf("mommy", "mama", "mom", "mother"),
            "daddy" to listOf("papa", "dad", "father"),
            "grandma" to listOf("grandmom", "grandmother", "nana", "granny"),
            "grandpa" to listOf("grandfather", "granddad", "papa"),
            "bro" to listOf("brother", "bhai"),
            "sis" to listOf("sister", "didi"),
            "hubby" to listOf("husband"),
            "wifey" to listOf("wife")
        )
        
        val words1 = str1.split(" ")
        val words2 = str2.split(" ")
        
        for (word1 in words1) {
            for (word2 in words2) {
                // Check direct phonetic matches
                phoneticVariations[word1]?.let { variations ->
                    if (variations.contains(word2) || word2 == word1) return 0.9
                }
                phoneticVariations[word2]?.let { variations ->
                    if (variations.contains(word1) || word1 == word2) return 0.9
                }
            }
        }
        
        return 0.0
    }
    
    private fun levenshteinDistance(str1: String, str2: String): Int {
        val dp = Array(str1.length + 1) { IntArray(str2.length + 1) }
        
        for (i in 0..str1.length) dp[i][0] = i
        for (j in 0..str2.length) dp[0][j] = j
        
        for (i in 1..str1.length) {
            for (j in 1..str2.length) {
                dp[i][j] = if (str1[i-1] == str2[j-1]) {
                    dp[i-1][j-1]
                } else {
                    1 + minOf(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
                }
            }
        }
        
        return dp[str1.length][str2.length]
    }
    
    private fun callContactByName(contactName: String, result: Result) {
        if (ContextCompat.checkSelfPermission(activity, Manifest.permission.READ_CONTACTS) 
            != PackageManager.PERMISSION_GRANTED) {
            result.error("PERMISSION_DENIED", "Contacts permission not granted", null)
            return
        }
        
        if (ContextCompat.checkSelfPermission(activity, Manifest.permission.CALL_PHONE) 
            != PackageManager.PERMISSION_GRANTED) {
            result.error("PERMISSION_DENIED", "Phone call permission not granted", null)
            return
        }
        
        try {
            // Get all contacts first for smart fuzzy matching
            val allContacts = mutableListOf<ContactInfo>()
            
            val cursor: Cursor? = activity.contentResolver.query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                arrayOf(
                    ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME,
                    ContactsContract.CommonDataKinds.Phone.NUMBER
                ),
                null,
                null,
                null
            )
            
            cursor?.use {
                val nameIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME)
                val numberIndex = it.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                
                while (it.moveToNext()) {
                    val name = it.getString(nameIndex)
                    val number = it.getString(numberIndex)
                    if (name != null && number != null) {
                        allContacts.add(ContactInfo(name, number))
                    }
                }
            }
            
            // Find best match using fuzzy matching
            val bestMatch = findBestContactMatch(contactName, allContacts)
            
            if (bestMatch != null) {
                // Make the call
                val callIntent = Intent(Intent.ACTION_CALL).apply {
                    data = Uri.parse("tel:${bestMatch.number}")
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                
                activity.startActivity(callIntent)
                val confidencePercent = (bestMatch.confidence * 100).toInt()
                result.success("Calling ${bestMatch.name} at ${bestMatch.number} (${confidencePercent}% match)")
            } else {
                result.error("CONTACT_NOT_FOUND", "No close match found for '$contactName'. Try being more specific.", null)
            }
        } catch (e: Exception) {
            result.error("CALL_ERROR", "Failed to call contact: ${e.message}", null)
        }
    }

    private fun sendSMSDirect(phoneNumber: String, message: String, result: Result) {
        try {
            // Check if we have SMS permission
            if (ContextCompat.checkSelfPermission(activity, Manifest.permission.SEND_SMS) 
                != PackageManager.PERMISSION_GRANTED) {
                result.error("PERMISSION_DENIED", "SMS permission not granted", null)
                return
            }
            
            // Use SmsManager to send SMS directly
            val smsManager = android.telephony.SmsManager.getDefault()
            
            // Split long messages if needed
            val parts = smsManager.divideMessage(message)
            if (parts.size == 1) {
                smsManager.sendTextMessage(phoneNumber, null, message, null, null)
            } else {
                smsManager.sendMultipartTextMessage(phoneNumber, null, parts, null, null)
            }
            
            result.success("SMS sent to $phoneNumber: \"$message\"")
        } catch (e: Exception) {
            result.error("SMS_ERROR", "Failed to send SMS: ${e.message}", null)
        }
    }

    private fun startVoiceRecognition(result: Result) {
        try {
            // Check if speech recognition is available
            if (!SpeechRecognizer.isRecognitionAvailable(activity)) {
                result.error("SPEECH_NOT_AVAILABLE", "Speech recognition not available on this device", null)
                return
            }

            // Store the result callback for later use
            speechRecognitionResult = result

            // Stop any existing recognition
            speechRecognizer?.destroy()

            // Create new speech recognizer (THIS RUNS IN BACKGROUND WITHOUT UI!)
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(activity)
            speechRecognizer?.setRecognitionListener(createRecognitionListener())

            // Create recognition intent (NO UI SHOWN!)
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                // Key setting: Don't show UI (same as MainActivity)
                putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, activity.packageName)
            }

            // Start listening without showing any UI - JARVIS overlay will show instead!
            speechRecognizer?.startListening(intent)
        } catch (e: Exception) {
            result.error("SPEECH_ERROR", "Failed to start speech recognition: ${e.message}", null)
        }
    }

    private fun createRecognitionListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                // Speech recognition is ready - JARVIS overlay is now visible
            }

            override fun onBeginningOfSpeech() {
                // User started speaking
            }

            override fun onRmsChanged(rmsdB: Float) {
                // Volume level changed - could be used for visual feedback in JARVIS overlay
            }

            override fun onBufferReceived(buffer: ByteArray?) {
                // Audio buffer received
            }

            override fun onEndOfSpeech() {
                // User stopped speaking
            }

            override fun onError(error: Int) {
                val result = speechRecognitionResult
                if (result != null) {
                    val errorMessage = when (error) {
                        SpeechRecognizer.ERROR_NO_MATCH -> "ERROR_NO_MATCH: No speech was recognized"
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "ERROR_SPEECH_TIMEOUT: Speech timeout"
                        SpeechRecognizer.ERROR_NETWORK -> "Network error"
                        SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                        SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                        SpeechRecognizer.ERROR_SERVER -> "Server error"
                        SpeechRecognizer.ERROR_CLIENT -> "Client error"
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Insufficient permissions"
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognition service busy"
                        else -> "Unknown error"
                    }
                    
                    // For timeout and no match errors, use specific error codes
                    val errorCode = when (error) {
                        SpeechRecognizer.ERROR_NO_MATCH, 
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "SPEECH_TIMEOUT"
                        else -> "SPEECH_ERROR"
                    }
                    
                    result.error(errorCode, errorMessage, null)
                    speechRecognitionResult = null
                }
            }

            override fun onResults(results: Bundle?) {
                val result = speechRecognitionResult
                if (result != null) {
                    val speechResults = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (speechResults != null && speechResults.isNotEmpty()) {
                        val recognizedText = speechResults[0]
                        result.success(recognizedText)
                    } else {
                        result.error("NO_SPEECH", "No speech was recognized", null)
                    }
                    speechRecognitionResult = null
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                // Handle partial results if needed
            }

            override fun onEvent(eventType: Int, params: Bundle?) {
                // Handle other events
            }
        }
    }

    private fun startAlwaysListen(result: Result) {
        if (isAlwaysListening) {
            result.success("Already listening")
            return
        }
        
        try {
            // Check for audio permissions
            if (ContextCompat.checkSelfPermission(activity, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(activity, arrayOf(Manifest.permission.RECORD_AUDIO), 1)
                result.error("PERMISSION_DENIED", "Audio recording permission required", null)
                return
            }
            
            // Check if we have background audio access (Android 10+)
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
                // Check if "Allow all the time" is enabled
                val audioManager = activity.getSystemService(Context.AUDIO_SERVICE) as AudioManager
                
                // Show user instructions for enabling "Allow all the time"
                activity.runOnUiThread {
                    android.app.AlertDialog.Builder(activity)
                        .setTitle("🎧 Enable Always Listening")
                        .setMessage("For JARVIS to listen while other apps are open:\n\n" +
                                   "📱 Steps:\n" +
                                   "1. Tap 'Open Settings' below\n" +
                                   "2. Go to 'Permissions' → 'Microphone'\n" +
                                   "3. Select 'Allow all the time' ⚡\n" +
                                   "4. Return to JARVIS and try again\n\n" +
                                   "⚠️ This is required for background voice recognition!")
                        .setPositiveButton("Open Settings") { _, _ ->
                            val intent = android.content.Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                            intent.data = android.net.Uri.fromParts("package", activity.packageName, null)
                            activity.startActivity(intent)
                        }
                        .setNegativeButton("Try Anyway") { _, _ ->
                            // Continue with service start
                            startListeningService(result)
                        }
                        .show()
                }
                return
            }
            
            // For older Android versions, start directly
            startListeningService(result)
            
        } catch (e: Exception) {
            result.error("ALWAYS_LISTEN_ERROR", "Failed to start always listening: ${e.message}", null)
        }
    }
    
    private fun startListeningService(result: Result) {
        try {
            // Set up callback for command processing
            JarvisListeningService.commandCallback = { command ->
                println("🎯 JARVIS: Received command from foreground service: '$command'")
                // Send command back to Flutter for processing
                methodChannel?.invokeMethod("onAlwaysListenCommand", command)
            }
            
            // Start foreground service
            val serviceIntent = Intent(activity, JarvisListeningService::class.java).apply {
                action = "START_LISTENING"
            }
            activity.startForegroundService(serviceIntent)
            
            isAlwaysListening = true
            result.success("Always listening started! JARVIS will listen for 'Jarvis...' commands in background.")
            
        } catch (e: Exception) {
            result.error("SERVICE_ERROR", "Failed to start listening service: ${e.message}", null)
        }
    }
    
    private fun stopAlwaysListen(result: Result) {
        isAlwaysListening = false
        
        // Stop foreground service
        val serviceIntent = Intent(activity, JarvisListeningService::class.java).apply {
            action = "STOP_LISTENING"
        }
        activity.startForegroundService(serviceIntent)
        
        // Clear callback
        JarvisListeningService.commandCallback = null
        
        result.success("Always listening stopped")
    }
    


    // 🎭 TONY STARK CONTAINER SYSTEM METHODS 🎭
    
    /**
     * Smart launcher that decides whether to use container or real app
     */
    private fun launchAppOrContainer(packageName: String, result: Result) {
        val appName = getAppNameFromPackage(packageName)
        
        // Check if this app should use container system
        if (shouldUseContainer(packageName)) {
            val appType = getAppTypeFromPackage(packageName)
            val startUrl = getDefaultUrlForApp(packageName)
            openContainer(appName, appType, startUrl, result)
        } else {
            // Use original app launching for system apps, utilities, etc.
            launchApp(packageName, result)
        }
    }
    
    /**
     * Open an app in our invisible container system
     */
    private fun openContainer(appName: String, appType: String, startUrl: String, result: Result) {
        try {
            // Check if container is already active
            if (ContainerActivity.isContainerActive(appName)) {
                result.success("$appName is already open")
                return
            }
            
            // Create container intent
            val containerIntent = Intent(activity, ContainerActivity::class.java).apply {
                putExtra("APP_NAME", appName)
                putExtra("APP_TYPE", appType)
                putExtra("START_URL", startUrl)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            
            activity.startActivity(containerIntent)
            result.success("✅ Opened $appName (container launched seamlessly)")
        } catch (e: Exception) {
            result.error("CONTAINER_ERROR", "Failed to open container for $appName: ${e.message}", null)
        }
    }
    
    /**
     * Close a container
     */
    private fun closeContainer(appName: String, result: Result) {
        Log.d("JARVIS_PLUGIN", "🎭 DEBUG: MobileControlPlugin.closeContainer called with '$appName'")
        val success = ContainerActivity.closeContainer(appName)
        Log.d("JARVIS_PLUGIN", "🎭 DEBUG: ContainerActivity.closeContainer returned: $success")
        
        if (success) {
            bringJarvisToForeground()
            result.success("✅ Closed $appName (container closed)")
        } else {
            result.success("$appName was not open in container")
        }
    }
    
    /**
     * Determine if app should use container system (Tony Stark intelligence!)
     */
    private fun shouldUseContainer(packageName: String): Boolean {
        val containerApps = setOf(
            "com.android.chrome",           // Chrome
            "com.chrome.beta"               // Chrome Beta
        )
        
        return containerApps.contains(packageName)
    }
    
    /**
     * Get app name from package name
     */
    private fun getAppNameFromPackage(packageName: String): String {
        return when (packageName) {
            "com.android.chrome", "com.chrome.beta" -> "Chrome"
            else -> packageName.substringAfterLast(".").replaceFirstChar { it.uppercase() }
        }
    }
    
    /**
     * Get app type for container
     */
    private fun getAppTypeFromPackage(packageName: String): String {
        return when (packageName) {
            "com.android.chrome", "com.chrome.beta", "com.opera.browser", 
            "org.mozilla.firefox", "com.brave.browser" -> "browser"
            "com.instagram.android" -> "instagram"
            "com.youtube.android" -> "youtube"
            "com.facebook.katana" -> "facebook"
            "com.twitter.android" -> "twitter"
            "com.whatsapp" -> "whatsapp"
            "com.netflix.mediaclient" -> "netflix"
            "com.amazon.mshop.android.shopping" -> "amazon"
            "com.spotify.music" -> "spotify"
            else -> "browser"
        }
    }
    
    /**
     * Get default URL for container apps
     */
    private fun getDefaultUrlForApp(packageName: String): String {
        return when (packageName) {
            "com.android.chrome", "com.chrome.beta", "com.opera.browser",
            "org.mozilla.firefox", "com.brave.browser" -> "https://www.google.com"
            "com.instagram.android" -> "https://www.instagram.com"
            "com.youtube.android" -> "https://www.youtube.com"
            "com.facebook.katana" -> "https://www.facebook.com"
            "com.twitter.android" -> "https://twitter.com"
            "com.whatsapp" -> "https://web.whatsapp.com"
            "com.netflix.mediaclient" -> "https://www.netflix.com"
            "com.amazon.mshop.android.shopping" -> "https://www.amazon.com"
            "com.spotify.music" -> "https://open.spotify.com"
            "com.google.android.apps.maps" -> "https://maps.google.com"
            "com.reddit.frontpage" -> "https://www.reddit.com"
            "com.pinterest" -> "https://www.pinterest.com"
            "com.linkedin.android" -> "https://www.linkedin.com"
            "com.microsoft.office.outlook" -> "https://outlook.live.com"
            else -> "https://www.google.com"
        }
    }
    
    /**
     * Bring JARVIS back to foreground (seamless experience)
     */
    private fun bringJarvisToForeground() {
        try {
            val jarvisIntent = activity.packageManager.getLaunchIntentForPackage(activity.packageName)
            jarvisIntent?.let { jarvisLaunch ->
                jarvisLaunch.flags = Intent.FLAG_ACTIVITY_NEW_TASK or 
                                   Intent.FLAG_ACTIVITY_SINGLE_TOP or 
                                   Intent.FLAG_ACTIVITY_CLEAR_TOP
                activity.startActivity(jarvisLaunch)
            }
        } catch (e: Exception) {
            // Silent fail - not critical
        }
    }
    
    /**
     * Original app launcher (for non-container apps)
     */
    private fun launchApp(packageName: String, result: Result) {
        try {
            val packageManager = activity.packageManager
            val launchIntent = packageManager.getLaunchIntentForPackage(packageName)
            
            if (launchIntent != null) {
                launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(launchIntent)
                result.success("App launched successfully")
            } else {
                // Try alternative method for system apps
                val intent = Intent().apply {
                    component = ComponentName.unflattenFromString(packageName)
                    addCategory(Intent.CATEGORY_LAUNCHER)
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                }
                
                try {
                    activity.startActivity(intent)
                    result.success("System app launched successfully")
                } catch (e: Exception) {
                    result.error("APP_NOT_FOUND", "App not installed or cannot be launched: $packageName", null)
                }
            }
        } catch (e: Exception) {
            result.error("LAUNCH_ERROR", "Failed to launch app: ${e.message}", null)
        }
    }

    // Clean up resources
    fun destroy() {
        isAlwaysListening = false
        speechRecognizer?.destroy()
        speechRecognizer = null
        speechRecognitionResult = null
        
        // Stop foreground service if running
        if (JarvisListeningService.isServiceRunning) {
            val serviceIntent = Intent(activity, JarvisListeningService::class.java).apply {
                action = "STOP_LISTENING"
            }
            activity.startForegroundService(serviceIntent)
        }
        JarvisListeningService.commandCallback = null
    }
} 