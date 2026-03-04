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

    channel_id = "mdm_agent_channel"
    channel_name = "MDM Agent Service"

    if Build.VERSION.SDK_INT >= 26:
        manager = cast("android.app.NotificationManager", service.getSystemService(Context.NOTIFICATION_SERVICE))
        channel = NotificationChannel(channel_id, channel_name, NotificationManager.IMPORTANCE_LOW)
        channel.setDescription("Enterprise management service")
        manager.createNotificationChannel(channel)

    notification = (
        Builder(service, channel_id)
        .setContentTitle("Device Managed")
        .setContentText("Compliance service is active")
        .setSmallIcon(R.drawable.icon)
        .setOngoing(True)
        .setPriority(-1)
        .build()
    )

    service.startForeground(1001, notification)


async def run_loop() -> None:
    from agent_logic import AgentLogic

    agent = AgentLogic()
    while True:
        try:
            await agent.run_once()
        except Exception as exc:
            print(f"Agent loop retry after error: {exc}")
        await asyncio.sleep(10)


if __name__ == "__main__":
    start_foreground_notification()
    asyncio.run(run_loop())
