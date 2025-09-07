import asyncio

from django.contrib.auth.models import User
from django.test import TransactionTestCase
from swarm.consumers import IN_MEMORY_CONVERSATIONS, DjangoChatConsumer
from swarm.models import ChatConversation, ChatMessage


class TestDjangoChatConsumer(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.conversation_id = 'test-conversation-123'
        # Clean up any existing conversations
        ChatConversation.objects.filter(student=self.user).delete()

    def test_fetch_conversation_from_memory(self):
        """Test fetching conversation from in-memory cache"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user
        consumer.conversation_id = self.conversation_id

        test_messages = [{'role': 'user', 'content': 'test'}]
        IN_MEMORY_CONVERSATIONS[self.conversation_id] = test_messages

        # Run async method in sync context
        result = asyncio.run(consumer.fetch_conversation(self.conversation_id))
        assert result == test_messages

        # Clean up
        del IN_MEMORY_CONVERSATIONS[self.conversation_id]

    def test_fetch_conversation_from_db(self):
        """Test fetching conversation from database"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        # Create test conversation
        conversation = ChatConversation.objects.create(
            conversation_id=self.conversation_id,
            student=self.user
        )
        ChatMessage.objects.create(
            conversation=conversation,
            sender='user',
            content='test message'
        )

        result = asyncio.run(consumer.fetch_conversation(self.conversation_id))
        assert len(result) == 1
        assert result[0]['role'] == 'user'
        assert result[0]['content'] == 'test message'

    def test_fetch_conversation_not_found(self):
        """Test fetching non-existent conversation returns empty list"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        result = asyncio.run(consumer.fetch_conversation('non-existent-id'))
        assert result == []

    def test_save_conversation(self):
        """Test saving conversation to database"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there'}
        ]

        asyncio.run(consumer.save_conversation(self.conversation_id, messages))

        # Verify conversation was created
        conversation = ChatConversation.objects.get(
            conversation_id=self.conversation_id,
            student=self.user
        )
        db_messages = list(conversation.messages.values('sender', 'content'))
        assert len(db_messages) == 2
        assert db_messages[0]['sender'] == 'user'
        assert db_messages[0]['content'] == 'Hello'

    def test_delete_conversation_with_messages(self):
        """Test deleting conversation that has messages (should not delete)"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        # Create conversation with messages
        conversation = ChatConversation.objects.create(
            conversation_id=self.conversation_id,
            student=self.user
        )
        ChatMessage.objects.create(
            conversation=conversation,
            sender='user',
            content='test'
        )

        asyncio.run(consumer.delete_conversation(self.conversation_id))

        # Conversation should still exist
        assert ChatConversation.objects.filter(
            conversation_id=self.conversation_id,
            student=self.user
        ).exists()

    def test_delete_empty_conversation(self):
        """Test deleting empty conversation"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        # Create empty conversation
        ChatConversation.objects.create(
            conversation_id=self.conversation_id,
            student=self.user
        )

        asyncio.run(consumer.delete_conversation(self.conversation_id))

        # Conversation should be deleted
        assert not ChatConversation.objects.filter(
            conversation_id=self.conversation_id,
            student=self.user
        ).exists()

    def test_delete_nonexistent_conversation(self):
        """Test deleting non-existent conversation (should not raise error)"""
        consumer = DjangoChatConsumer()
        consumer.user = self.user

        # Should not raise exception
        asyncio.run(consumer.delete_conversation('non-existent-id'))
