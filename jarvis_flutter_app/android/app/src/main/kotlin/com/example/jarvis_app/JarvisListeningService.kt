package com.example.jarvis_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.IBinder
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import android.Manifest
import java.util.Locale
import android.os.Handler
import android.os.Looper

class JarvisListeningService : Service() {
    
    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    
    companion object {
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "jarvis_listening_channel"
        private const val CHANNEL_NAME = "JARVIS Always Listening"
        
        var isServiceRunning = false
        var commandCallback: ((String) -> Unit)? = null
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        println("🎧 JARVIS: Listening service created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_LISTENING" -> {
                startForegroundListening()
            }
            "STOP_LISTENING" -> {
                stopForegroundListening()
            }
        }
        return START_STICKY // Restart service if killed
    }
    
    private fun startForegroundListening() {
        if (isServiceRunning) {
            println("🎧 JARVIS: Service already running")
            return
        }
        
        // Check audio permission
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED) {
            println("🎧 JARVIS: No audio permission for background service")
            stopSelf()
            return
        }
        
        val notification = createNotification("🎧 Always listening for 'Jarvis...' commands")
        startForeground(NOTIFICATION_ID, notification)
        
        initializeSpeechRecognizer()
        startListening()
        isServiceRunning = true
        
        println("🎧 JARVIS: Foreground listening service started")
    }
    
    private fun stopForegroundListening() {
        isListening = false
        speechRecognizer?.cancel()
        speechRecognizer?.destroy()
        speechRecognizer = null
        
        stopForeground(true)
        isServiceRunning = false
        
        println("🎧 JARVIS: Foreground listening service stopped")
        stopSelf()
    }
    
    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "JARVIS background voice listening"
            setSound(null, null)
            enableVibration(false)
        }
        
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(channel)
    }
    
    private fun createNotification(text: String): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("JARVIS Always Listening")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }
    
    private fun initializeSpeechRecognizer() {
        speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
        
        if (speechRecognizer == null) {
            println("🎧 JARVIS: Speech recognizer not available")
            stopSelf()
            return
        }
        
        speechRecognizer?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                println("🎧 JARVIS: Background service ready for speech")
                updateNotification("🎧 Listening... Say 'Jarvis [command]'")
            }
            
            override fun onBeginningOfSpeech() {
                println("🎧 JARVIS: Background speech detected")
                updateNotification("🎧 Speech detected...")
            }
            
            override fun onRmsChanged(rmsdB: Float) {
                // Voice level monitoring
            }
            
            override fun onBufferReceived(buffer: ByteArray?) {
                // Audio buffer
            }
            
            override fun onEndOfSpeech() {
                println("🎧 JARVIS: Background speech ended")
                updateNotification("🎧 Processing speech...")
            }
            
            override fun onError(error: Int) {
                println("🎧 JARVIS: Background listening error: $error")
                updateNotification("🎧 Listening error, restarting...")
                
                // Restart listening after error (except timeout/no speech)
                if (isServiceRunning && isListening && 
                    error != SpeechRecognizer.ERROR_SPEECH_TIMEOUT && 
                    error != SpeechRecognizer.ERROR_NO_MATCH) {
                    restartListening()
                }
            }
            
            override fun onResults(results: Bundle?) {
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if (matches != null && matches.isNotEmpty()) {
                    val spokenText = matches[0].lowercase()
                    println("🎧 JARVIS: Background service heard: '$spokenText'")
                    
                    // Check for "Jarvis" wake word
                    if (spokenText.startsWith("jarvis ")) {
                        val command = spokenText.removePrefix("jarvis ").trim()
                        println("🎯 JARVIS: Background wake word detected! Command: '$command'")
                        
                        updateNotification("🎯 Command detected: $command")
                        
                        // Background current app and bring JARVIS to foreground
                        backgroundCurrentAppAndShowJarvis()
                        
                        // Send command to callback
                        commandCallback?.invoke(command)
                        
                        // Brief pause before restarting listening
                        Handler(Looper.getMainLooper()).postDelayed({
                            updateNotification("🎧 Always listening for 'Jarvis...' commands")
                        }, 2000)
                    } else {
                        updateNotification("🎧 Always listening for 'Jarvis...' commands")
                    }
                }
                
                // Restart listening if still active
                if (isServiceRunning && isListening) {
                    restartListening()
                }
            }
            
            override fun onPartialResults(partialResults: Bundle?) {
                // Partial results
            }
            
            override fun onEvent(eventType: Int, params: Bundle?) {
                // Handle other events
            }
        })
    }
    
    private fun startListening() {
        if (!isServiceRunning || isListening) return
        
        isListening = true
        
        try {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            }
            
            speechRecognizer?.startListening(intent)
            println("🎧 JARVIS: Background listening started")
        } catch (e: Exception) {
            println("🎧 JARVIS: Error starting background listening: ${e.message}")
            isListening = false
        }
    }
    
    private fun restartListening() {
        if (!isServiceRunning) return
        
        isListening = false
        speechRecognizer?.cancel()
        
        // Small delay before restarting
        Handler(Looper.getMainLooper()).postDelayed({
            if (isServiceRunning) {
                startListening()
            }
        }, 1000)
    }
    
    private fun updateNotification(text: String) {
        val notification = createNotification(text)
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }
    
    private fun backgroundCurrentAppAndShowJarvis() {
        try {
            // Move current app to background (home button simulation)
            val homeIntent = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            startActivity(homeIntent)
            
            // Bring JARVIS to foreground after delay
            Handler(Looper.getMainLooper()).postDelayed({
                val jarvisIntent = Intent(this, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or Intent.FLAG_ACTIVITY_NEW_TASK
                }
                startActivity(jarvisIntent)
                println("🎯 JARVIS: Brought to foreground via background service")
            }, 500)
            
        } catch (e: Exception) {
            println("🎯 JARVIS: Error backgrounding app from service: ${e.message}")
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        stopForegroundListening()
        println("🎧 JARVIS: Listening service destroyed")
    }
} 