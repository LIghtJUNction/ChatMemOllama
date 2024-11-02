import threading
import time

class Logger:
    # 定义日志级别
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    level_names = {
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARNING: 'WARNING',
        ERROR: 'ERROR',
        CRITICAL: 'CRITICAL'
    }

    def __init__(self, filename='app.log', buffer_size=100, flush_interval=5, level=INFO):
        """
        初始化日志类。

        :param filename: 日志文件名，默认 'app.log'。
        :param buffer_size: 缓冲区大小，达到此数量的日志时触发写入。
        :param flush_interval: 刷新间隔（秒），超过此时间间隔将触发写入。
        :param level: 日志级别，低于此级别的日志将被忽略，默认 INFO。
        """
        self.filename = filename
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.level = level
        self.log_buffer = []
        self.lock = threading.Lock()
        self.last_flush_time = time.time()

    def log(self, message, level=INFO):
        """
        记录一条日志信息。

        :param message: 要记录的日志消息。
        :param level: 日志级别，默认为 INFO。
        """
        if level < self.level:
            return  # 忽略低于当前日志级别的消息

        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        level_name = self.level_names.get(level, 'INFO')
        log_entry = f'[{timestamp}] [{level_name}] {message}'
        with self.lock:
            self.log_buffer.append(log_entry)
            current_time = time.time()
            if len(self.log_buffer) >= self.buffer_size or \
               (current_time - self.last_flush_time) >= self.flush_interval:
                self.flush()
                self.last_flush_time = current_time

    def debug(self, message):
        self.log(message, level=self.DEBUG)

    def info(self, message):
        self.log(message, level=self.INFO)

    def warning(self, message):
        self.log(message, level=self.WARNING)

    def error(self, message):
        self.log(message, level=self.ERROR)

    def critical(self, message):
        self.log(message, level=self.CRITICAL)

    def flush(self):
        """
        将缓冲区中的日志写入文件。
        """
        with self.lock:
            if self.log_buffer:
                with open(self.filename, 'a', encoding='utf-8') as f:
                    f.write('\n'.join(self.log_buffer) + '\n')
                self.log_buffer.clear()

    def close(self):
        """
        关闭日志类，确保所有日志被写入文件。
        """
        self.flush()