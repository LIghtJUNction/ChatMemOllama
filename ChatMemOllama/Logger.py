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

    def __init__(self, filename='./ChatMemOllama/ChatMemOllama.log', buffer_size=100, flush_interval=10, level=INFO):
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
        self.running = True
        
        self.flush_thread = threading.Thread(target=self._auto_flush)
        self.flush_thread.start()
        print("Flush thread started")

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
        print(f"[DEBUG] {message}")

    def info(self, message):
        self.log(message, level=self.INFO)
        print(f"[INFO] {message}")

    def warning(self, message):
        self.log(message, level=self.WARNING)
        print(f"[WARNING] {message}")

    def error(self, message):
        self.log(message, level=self.ERROR)
        print(f"[ERROR] {message}")

    def critical(self, message):
        self.log(message, level=self.CRITICAL)
        print(f"[CRITICAL] {message}")

    def flush(self):
        print("Attempting to flush logs")
        try:
            with self.lock:
                print("Lock acquired for flushing")
                if self.log_buffer:
                    print("Opening log file for writing")
                    with open(self.filename, 'a', encoding='utf-8') as f:
                        print("Writing logs to file")
                        f.write('\n'.join(self.log_buffer) + '\n')
                    self.log_buffer.clear()
                    self.last_flush_time = time.time()
        except Exception as e:
            print(f"Flush exception: {e}")

    def _limit_log_file(self):
        """
        限制日志文件的总行数为100行，保留最新的100行。
        """
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if len(lines) > 100:
                print("Limiting log file to the last 100 lines")
                lines = lines[-100:]
                with open(self.filename, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
        except Exception as e:
            print(f"Limit log file exception: {e}")

    def _auto_flush(self):
        print("Auto flush thread started")
        while self.running:
            time.sleep(1)
            if time.time() - self.last_flush_time >= self.flush_interval:
                print("Auto flushing logs")
                self.flush()

    def close(self):
        """
        关闭日志类，确保所有日志被写入文件。
        """
        print("Closing logger")
        self.running = False
        self.flush_thread.join()
        self.flush()

if __name__ == "__main__":
    logger = Logger()
    logger.info('This is an information message.')
    logger.warning('This is a warning message.')
    logger.error('This is an error message.')
    logger.critical('This is a critical message.')
    # debug
    print(logger.__dict__)

    n = 1
    try:
        while True:
            time.sleep(1)
            logger.info(f' test --- {n}')
            n += 1
    except KeyboardInterrupt:
        print("用户中断程序")
    finally:
        logger.close()