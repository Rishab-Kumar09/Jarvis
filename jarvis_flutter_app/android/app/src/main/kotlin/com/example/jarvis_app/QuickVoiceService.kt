package com.example.jarvis_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat

class QuickVoiceService : Service() {
    
    companion object {
        private const val NOTIFICATION_ID = 1002
        private const val CHANNEL_ID = "jarvis_quick_voice_channel"
        private const val CHANNEL_NAME = "JARVIS Quick Voice"
        
        var isServiceRunning = false
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        println("🎤 JARVIS: Quick Voice service created")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "START_QUICK_VOICE" -> {
                startQuickVoiceNotification()
            }
            "STOP_QUICK_VOICE" -> {
                stopQuickVoiceNotification()
            }
            "TRIGGER_VOICE" -> {
                triggerVoiceCommand()
            }
        }
        return START_STICKY
    }
    
    private fun startQuickVoiceNotification() {
        if (isServiceRunning) return
        
        val notification = createQuickVoiceNotification()
        startForeground(NOTIFICATION_ID, notification)
        isServiceRunning = true
        
        println("🎤 JARVIS: Quick Voice notification active")
    }
    
    private fun stopQuickVoiceNotification() {
        stopForeground(true)
        isServiceRunning = false
        stopSelf()
        println("🎤 JARVIS: Quick Voice notification stopped")
    }
    
    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            CHANNEL_NAME,
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "JARVIS Quick Voice Actions"
            setSound(null, null)
            enableVibration(false)
        }
        
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.createNotificationChannel(channel)
    }
    
    private fun createQuickVoiceNotification(): Notification {
        // Main app intent
        val openAppIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val openAppPendingIntent = PendingIntent.getActivity(
            this, 0, openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        // Voice command intent
        val voiceIntent = Intent(this, QuickVoiceService::class.java).apply {
            action = "TRIGGER_VOICE"
        }
        val voicePendingIntent = PendingIntent.getService(
            this, 1, voiceIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("🤖 JARVIS Quick Voice")
            .setContentText("Tap 🎤 for voice command or 📱 to open app")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(openAppPendingIntent)
            .addAction(
                android.R.drawable.ic_btn_speak_now,
                "🎤 Voice Command",
                voicePendingIntent
            )
            .addAction(
                android.R.drawable.ic_menu_view,
                "📱 Open JARVIS",
                openAppPendingIntent
            )
            .setOngoing(true)
            .setAutoCancel(false)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()
    }
    
    private fun triggerVoiceCommand() {
        try {
            println("🎤 JARVIS: Quick Voice triggered - bringing app to foreground")
            
            // Background current app
            val homeIntent = Intent(Intent.ACTION_MAIN).apply {
                addCategory(Intent.CATEGORY_HOME)
                flags = Intent.FLAG_ACTIVITY_NEW_TASK
            }
            startActivity(homeIntent)
            
            // Brief delay, then bring JARVIS to foreground
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                val jarvisIntent = Intent(this, MainActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_REORDER_TO_FRONT or Intent.FLAG_ACTIVITY_NEW_TASK
                    putExtra("TRIGGER_VOICE_COMMAND", true)
                }
                startActivity(jarvisIntent)
                println("🎤 JARVIS: App brought to foreground for voice command")
            }, 300)
            
        } catch (e: Exception) {
            println("🎤 JARVIS: Error triggering voice command: ${e.message}")
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        isServiceRunning = false
        println("🎤 JARVIS: Quick Voice service destroyed")
    }
} 