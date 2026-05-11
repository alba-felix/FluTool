import sys
import random
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt5.QtCore import QTimer, Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QColor, QBrush, QFont, QPen

class SnakeGame(QWidget):
    def __init__(self):
        super().__init__()
        # 游戏窗口大小（像素）
        self.WIDTH = 600
        self.HEIGHT = 600
        # 格子尺寸（像素）
        self.GRID_SIZE = 25
        # 网格行列数
        self.COLS = self.WIDTH // self.GRID_SIZE   # 24
        self.ROWS = self.HEIGHT // self.GRID_SIZE  # 24

        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowTitle("贪吃蛇 - PyQt5 Demo")
        self.setStyleSheet("background-color: black;")

        # 初始化游戏状态
        self.init_game()

        # 定时器，控制游戏循环（移动速度）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.move_snake)
        self.timer.start(150)  # 毫秒

        # 开启键盘监听
        self.setFocusPolicy(Qt.StrongFocus)

    def init_game(self):
        """初始化或重置游戏数据"""
        # 蛇的初始位置（坐标列表，每个元素是QPoint）
        self.snake = [
            QPoint(self.COLS // 2, self.ROWS // 2),          # 蛇头
            QPoint(self.COLS // 2 - 1, self.ROWS // 2),
            QPoint(self.COLS // 2 - 2, self.ROWS // 2)
        ]
        self.direction = Qt.Key_Right   # 当前移动方向
        self.next_direction = Qt.Key_Right
        self.score = 0
        self.game_over = False

        # 生成第一个食物
        self.food = self.generate_food()

    def generate_food(self):
        """在空闲位置随机生成食物"""
        # 得到蛇占用的所有坐标
        occupied = [p for p in self.snake]
        while True:
            x = random.randint(0, self.COLS - 1)
            y = random.randint(0, self.ROWS - 1)
            candidate = QPoint(x, y)
            if candidate not in occupied:
                return candidate

    def move_snake(self):
        """蛇移动的核心逻辑（每帧调用）"""
        if self.game_over:
            return

        # 应用方向（防止在同一个时钟周期内多次改变方向造成的自我碰撞）
        self.direction = self.next_direction

        # 计算新蛇头的位置
        head = self.snake[0]
        new_head = QPoint(head.x(), head.y())
        if self.direction == Qt.Key_Up:
            new_head.setY(head.y() - 1)
        elif self.direction == Qt.Key_Down:
            new_head.setY(head.y() + 1)
        elif self.direction == Qt.Key_Left:
            new_head.setX(head.x() - 1)
        elif self.direction == Qt.Key_Right:
            new_head.setX(head.x() + 1)

        # 检查是否吃到食物
        ate_food = (new_head == self.food)

        # 插入新头
        self.snake.insert(0, new_head)
        if not ate_food:
            # 没吃到食物就移除尾部
            self.snake.pop()
        else:
            # 吃了食物，分数+1，生成新食物，尾部不删除所以长度+1
            self.score += 1
            self.food = self.generate_food()

        # 碰撞检测（边界 / 自身）
        if self.check_collision():
            self.game_over = True
            self.timer.stop()
            self.show_game_over_dialog()

        # 刷新界面
        self.update()

    def check_collision(self):
        """检测是否撞墙或撞到自己"""
        head = self.snake[0]
        # 边界碰撞
        if (head.x() < 0 or head.x() >= self.COLS or
            head.y() < 0 or head.y() >= self.ROWS):
            return True
        # 自身碰撞：检查蛇头是否和身体某一部分重叠（注意蛇头索引0）
        for i in range(1, len(self.snake)):
            if self.snake[i] == head:
                return True
        return False

    def keyPressEvent(self, event):
        """处理键盘方向键，禁止原地掉头"""
        key = event.key()
        if self.game_over:
            # 游戏结束后按任意键可重置（或者点击对话框）
            return
        # 不允许原地掉头
        if (key == Qt.Key_Up and self.direction != Qt.Key_Down) or \
           (key == Qt.Key_Down and self.direction != Qt.Key_Up) or \
           (key == Qt.Key_Left and self.direction != Qt.Key_Right) or \
           (key == Qt.Key_Right and self.direction != Qt.Key_Left):
            self.next_direction = key

    def paintEvent(self, event):
        """绘制游戏画面：蛇、食物、分数"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制网格线（可选，便于观察格子）
        pen = QPen(QColor(40, 40, 40), 1, Qt.SolidLine)
        painter.setPen(pen)
        for x in range(0, self.WIDTH, self.GRID_SIZE):
            painter.drawLine(x, 0, x, self.HEIGHT)
        for y in range(0, self.HEIGHT, self.GRID_SIZE):
            painter.drawLine(0, y, self.WIDTH, y)

        # 绘制食物（红色圆角矩形）
        painter.setBrush(QBrush(QColor(255, 50, 50)))
        painter.setPen(Qt.NoPen)
        food_rect = self.grid_to_rect(self.food)
        painter.drawRoundedRect(food_rect, 5, 5)

        # 绘制蛇（绿色渐变）
        for i, point in enumerate(self.snake):
            if i == 0:  # 蛇头用亮绿色
                painter.setBrush(QBrush(QColor(80, 255, 80)))
            else:
                painter.setBrush(QBrush(QColor(30, 180, 30)))
            rect = self.grid_to_rect(point)
            painter.drawRoundedRect(rect, 4, 4)

        # 绘制分数
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(10, 40, f"Score: {self.score}")

        # 如果游戏结束，显示提示文字
        if self.game_over:
            painter.setPen(QPen(QColor(255, 100, 100)))
            painter.setFont(QFont("Arial", 24, QFont.Bold))
            painter.drawText(self.WIDTH//2 - 100, self.HEIGHT//2, "GAME OVER")

    def grid_to_rect(self, point):
        """将网格坐标转换为矩形绘制区域"""
        x = point.x() * self.GRID_SIZE
        y = point.y() * self.GRID_SIZE
        return QRect(x, y, self.GRID_SIZE, self.GRID_SIZE)

    def show_game_over_dialog(self):
        """弹出游戏结束对话框，提供重新开始选项"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("游戏结束")
        msg_box.setText(f"最终得分：{self.score}\n是否重新开始？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply = msg_box.exec_()
        if reply == QMessageBox.Yes:
            self.reset_game()
        else:
            self.close()

    def reset_game(self):
        """重置游戏状态并重新开始"""
        self.timer.stop()
        self.init_game()
        self.timer.start(150)
        self.update()

def main():
    app = QApplication(sys.argv)
    window = SnakeGame()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()