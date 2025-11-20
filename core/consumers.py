"""
实时通信
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # 获取 URL 路由参数
            self.doctor_id = self.scope['url_route']['kwargs']['doctor_id']
            self.patient_id = self.scope['url_route']['kwargs']['patient_id']

            # 为每个病人和医生创建房间名
            self.room_name = f"doctor_{self.doctor_id}_patient_{self.patient_id}"
            self.room_group_name = f"chat_{self.room_name}"

            # 将当前 WebSocket 连接加入到房间组
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # 接受 WebSocket 连接
            await self.accept()
            print(f"WebSocket connected to {self.room_group_name}")
        except Exception as e:
            print(f"Error during connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        # 离开房间组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # 处理接收到的消息，确保数据格式完整
        try:
            text_data_json = json.loads(text_data)

            # 从接收到的消息中提取字段
            message = text_data_json.get('message', '')
            send_time = text_data_json.get('send_time', datetime.now().isoformat())
            sender_id = text_data_json.get('sender_id', None)
            is_text = text_data_json.get('is_text', True)
            file_url = text_data_json.get('file_url', None)

            # 发送消息到房间组，携带完整的字段信息
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'send_time': send_time,
                    'sender_id': sender_id,
                    'is_text': is_text,
                    'file_url': file_url
                }
            )
        except Exception as e:
            print(f"Error receiving message: {e}")

    async def chat_message(self, event):
        # 从房间组接收到的消息中提取字段
        message = event['message']
        send_time = event['send_time']
        sender_id = event['sender_id']
        is_text = event['is_text']
        file_url = event['file_url']

        # 发送消息到 WebSocket，包含所有字段
        await self.send(text_data=json.dumps({
            'message': message,
            'send_time': send_time,
            'sender_id': sender_id,
            'is_text': is_text,
            'file_url': file_url
        }))
