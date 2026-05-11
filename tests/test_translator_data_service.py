from storage import DatabaseManager
from plugins.text_tools.translator_data_service import TranslatorDataService


def reset_database_singleton():
    """重置数据库单例，避免测试间共享状态"""
    DatabaseManager.reset_instance()


def test_translator_data_service_history_and_vocabulary_flow(tmp_path):
    """翻译数据服务覆盖历史和单词本基础链路"""
    reset_database_singleton()
    db = DatabaseManager()
    db.initialize(str(tmp_path / "translator_data_service.db"))
    service = TranslatorDataService(db)
    service.initialize_tables()

    history_id = service.add_history("hello", "你好", "英语", "中文")
    history = service.list_history("英语→中文")
    assert history[0]["id"] == history_id
    assert history[0]["target_text"] == "你好"

    vocab_id = service.add_vocabulary("hello", "你好", "来自测试")
    vocab = service.get_vocabulary(vocab_id)
    assert vocab["word"] == "hello"
    assert service.vocabulary_exists("hello")

    assert service.update_vocabulary(vocab_id, "hello", "您好", "更新")
    assert service.list_vocabulary()[0]["translation"] == "您好"

    assert service.delete_vocabulary(vocab_id)
    assert service.list_vocabulary() == []

    assert service.delete_history(history_id)
    assert service.list_history() == []
    reset_database_singleton()
