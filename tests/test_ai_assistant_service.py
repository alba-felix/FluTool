from storage import DatabaseManager
from plugins.ai_assistant.service import AIAssistantService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_ai_assistant_service_conversation_message_flow(tmp_path):
    """AI 助手服务覆盖对话和消息基础链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "ai_assistant_service.db"))
    service = AIAssistantService(db)

    conversation_id = service.add_conversation("测试对话", "test_provider", "test_model")
    assert service.get_conversations()[0]["id"] == conversation_id

    message_id = service.add_message(conversation_id, "user", "hello")
    messages = service.get_messages(conversation_id)
    assert messages[0]["id"] == message_id
    assert service.get_message_count(conversation_id) == 1

    assert service.update_conversation(conversation_id, title="新标题")
    assert service.search_conversations("新标题")[0]["id"] == conversation_id

    assert service.delete_conversation(conversation_id)
    assert service.get_conversations() == []
    reset_database_singleton()
