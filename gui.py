from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment, Message
from nonebot.params import CommandArg
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import random
import json
import asyncio
from pathlib import Path

# 定义turtle目录，相对于当前脚本gui.py所在目录
TURTLE_DIR = Path(__file__).parent / "turtle"

gui = on_command("gui")

def read_json(file_path: Path):
    """读取JSON文件并返回数据"""
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(file_path: Path, data):
    """写入数据到JSON文件"""
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_info_image(m, guinfo, uid, output_path: Path):
    """
    根据房间数据m和龟的信息guinfo生成房间信息图片，
    并将生成的图片保存到output_path，返回该路径
    """
    # 加载资源图片和字体（所有文件均在TURTLE_DIR中）
    img_line = Image.open(TURTLE_DIR / "line.bmp")
    bg_image = Image.open(TURTLE_DIR / "bg.bmp").copy().resize((1400, 770))
    setFont1 = ImageFont.truetype(str(TURTLE_DIR / "got2.ttf"), 83)
    setFont2 = ImageFont.truetype(str(TURTLE_DIR / "got2.ttf"), 43)

    draw = ImageDraw.Draw(bg_image)
    room_owner = m.get("orner", uid)
    draw.text((0, 0), f"赛龟房间 #{room_owner}", font=setFont1, fill="#1f1e33")

    guinum = m["guinum"]
    for i in range(6):
        turtle_idx = guinum[i]
        turtle_info = guinfo["info"][turtle_idx]
        spd_basic = int(turtle_info["spd"] * 2 + turtle_info["bas"] * 8)
        spd_max = turtle_info["spd"] * 10 + turtle_info["bas"] * 8
        draw.text((0, 110 + i * 110), f"{i}号跑道: {turtle_info['name']}", font=setFont2, fill="#1f1e33")
        draw.text((500, 110 + i * 110), f"速度：", font=setFont2, fill="#1f1e33")
        draw.rectangle([(650, 120 + i * 110),(651 + spd_basic, 156 + i * 110)],fill="#353535", outline="#353535", width=2)
        draw.rectangle([(650, 120 + i * 110),(651 + spd_max, 156 + i * 110)], outline="#ff0000", width=2)
        draw.text((0, 155 + i * 110), f"技能:{turtle_info['des']}", font=setFont2, fill="#1f1e33")
        # 加载并调整龟的图片
        turtle_img = Image.open(TURTLE_DIR / f"kame{turtle_idx}.png")
        turtle_img_resized = turtle_img.resize((100, 100))
        bg_image.paste(turtle_img_resized, (1300, i * 110 + 110), turtle_img_resized)
        # 绘制跑道分割线
        bg_image.paste(img_line.resize((1400, 8)), (0, i * 110 + 100))

    final_image = bg_image.resize((700, 385))
    final_image.save(output_path)
    return output_path


@gui.handle()
async def handle_first_receive(matcher: Matcher, event: Event, text: Message = CommandArg()):
    # 定义各个文件的路径（均为相对gui.py的TURTLE_DIR）
    gui_json_path = TURTLE_DIR / "gui.json"
    room_json_path = TURTLE_DIR / "gyi.json"
    info_image_path = TURTLE_DIR / "info.png"

    uid = event.get_user_id()
    text_str = str(text).strip()

    # ---------- 创建房间（随机选择参赛龟） ----------
    if text_str == "start":
        if room_json_path.exists():
            await gui.finish("房间已存在")
        guinfo = read_json(gui_json_path)
        m_data = {
            "orner": uid,
            "guinum": [int(random.random() * len(guinfo["info"])) for _ in range(6)],
            "bet": [[] for _ in range(6)]
        }
        write_json(room_json_path, m_data)
        generate_info_image(m_data, guinfo, uid, info_image_path)
        await gui.finish(MessageSegment.image(info_image_path.resolve().as_uri()))

    # ---------- 创建房间（自定义选择参赛龟） ----------
    if text_str.startswith("startc"):
        if room_json_path.exists():
            await gui.finish("房间已存在")
        guinfo = read_json(gui_json_path)
        parts = text_str.split()
        if len(parts) != 7:
            await gui.finish("格式错误")
        try:
            custom_guinum = [int(parts[i + 1]) for i in range(6)]
        except ValueError:
            await gui.finish("跑道编号必须为数字")
        m_data = {
            "orner": uid,
            "guinum": custom_guinum,
            "bet": [[] for _ in range(6)]
        }
        write_json(room_json_path, m_data)
        generate_info_image(m_data, guinfo, uid, info_image_path)
        await gui.finish(MessageSegment.image(info_image_path.resolve().as_uri()))

    # ---------- 查看房间信息 ----------
    if text_str == "info":
        if not room_json_path.exists():
            await gui.finish("房间不存在")
        guinfo = read_json(gui_json_path)
        m_data = read_json(room_json_path)
        generate_info_image(m_data, guinfo, uid, info_image_path)
        await gui.finish(MessageSegment.image(info_image_path.resolve().as_uri()))

    # ---------- 投注 ----------
    if text_str.startswith("bet"):
        if not room_json_path.exists():
            await gui.finish("请先创建房间")
        parts = text_str.split()
        if len(parts) < 2:
            await gui.finish("请输入跑道编号")
        try:
            bet_index = int(parts[1])
        except ValueError:
            await gui.finish("跑道编号必须为数字")
        m_data = read_json(room_json_path)
        for bets in m_data["bet"]:
            if uid in bets:
                await gui.finish("您已经进行了一次猜测，请等待比赛开始")
        if bet_index < 0 or bet_index >= 6:
            await gui.finish("跑道编号错误")
        m_data["bet"][bet_index].append(uid)
        write_json(room_json_path, m_data)
        await gui.finish(f"您选择了{bet_index}号跑道")

    # ---------- 开始比赛 ----------
    if text_str == "go":
        if not room_json_path.exists():
            await gui.finish("请先创建房间")
        m_data = read_json(room_json_path)
        if not (m_data["orner"] == uid or uid in ["2242022366", "1481618319"]):
            await gui.finish("请房主开始比赛")
        # 删除房间文件，防止重复操作
        room_json_path.unlink(missing_ok=True)

        random.seed(datetime.now().timestamp())
        run_positions = [0] * 6  # 各龟位置
        frame_index = 0
        race_over = False
        images = []
        img_line = Image.open(TURTLE_DIR / "line.bmp")
        guinfo = read_json(gui_json_path)
        guinum = m_data["guinum"]
        setFont = ImageFont.truetype(str(TURTLE_DIR / "got2.ttf"), 28)
        trick_room = 0  # 特殊标识

        # 定义各个技能函数
        def noSkl(gid, t):
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def percSpd(gid, t):
            g_val = int(random.random() * 10000)
            if g_val < guinfo["info"][guinum[gid]]["arg1"] * 100:
                skill_spd[gid] += guinfo["info"][guinum[gid]]["arg2"]
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def fixSpd(gid, t):
            basic_speed[gid] += guinfo["info"][guinum[gid]]["arg1"]

        def getRnk():
            ranks = [0] * 7
            currentPos = 1
            for pos in range(1500, -1500, -1):
                for j in range(6):
                    if run_positions[j] == pos:
                        ranks[currentPos] = j
                        currentPos += 1
                if currentPos == 7:
                    break
            return ranks

        def posSpd(gid, t):
            
            currentPos = 1
            ranks = [0] * 7
            if guinfo["info"][guinum[gid]]["arg1"] > 0:
                for pos in range(1500, -1000, -1):
                    for j in range(6):
                        if run_positions[j] == pos:
                            ranks[j] = currentPos
                            currentPos += 1
                    if currentPos == 7:
                        break
                if ranks[gid] <= guinfo["info"][guinum[gid]]["arg1"]:
                    skill_spd[gid] += guinfo["info"][guinum[gid]]["arg2"]
            else:
                for pos in range(-1000, 1500):
                    for j in range(6):
                        if run_positions[j] == pos:
                            ranks[j] = currentPos
                            currentPos += 1
                            break
                    if currentPos == 7:
                        break
                if ranks[gid] <= abs(guinfo["info"][guinum[gid]]["arg1"]):
                    skill_spd[gid] += guinfo["info"][guinum[gid]]["arg2"]
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def mudSkill(gid, t):
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)
            skill_spd[gid - 1] -= guinfo["info"][guinum[gid]]["arg1"]
            skill_spd[(gid + 1) % 6] -= guinfo["info"][guinum[gid]]["arg1"]

        def trickroomSkill(gid, t):
            
            trick_room = 1
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2+ guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def posAtk(gid, t):
            ranks = getRnk()
            if guinfo["info"][guinum[gid]]["arg1"] >= 0:
                for i in range(1, guinfo["info"][guinum[gid]]["arg1"] + 1):
                    if ranks[i] != gid:
                        skill_spd[ranks[i]] -= guinfo["info"][guinum[gid]]["arg2"]
            else:
                for i in range(-1, guinfo["info"][guinum[gid]]["arg1"] - 1, -1):
                    if ranks[i] != gid:
                        skill_spd[ranks[i]] -= guinfo["info"][guinum[gid]]["arg2"]
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2+ guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def clearanceSkill(gid, t):
            if skill_spd[gid] < 0:
                skill_spd[gid] = 0
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)

        def skillFactorModify(gid, t):
            for i in range(6):
                skill_spd[i] = int(skill_spd[i] * guinfo["info"][guinum[gid]]["arg1"] / 100.0)
            basic_speed[gid] += int(random.random() * guinfo["info"][guinum[gid]]["spd"] * 1.2 + guinfo["info"][guinum[gid]][
                "bas"] + guinfo["info"][guinum[gid]]["spd"] * 0.4)
            
        def halfHalf(gid, t):
            g_val = int(random.random() * 10000)
            basic_speed[gid] += guinfo["info"][guinum[gid]]["arg1"] if g_val > 5000 else guinfo["info"][guinum[gid]]["arg2"]

        # 技能函数映射，正负值均可通过负索引访问对应函数
        skill_functions = [percSpd, fixSpd, posSpd, mudSkill, posAtk, trickroomSkill, halfHalf, skillFactorModify, clearanceSkill, noSkl]

        # 模拟比赛帧（每帧生成一张图片）
        while True:
            basic_speed = [0] * 6
            skill_spd = [0] * 6
            frame_image = Image.open(TURTLE_DIR / "bg.bmp").copy().resize((500, 300))
            draw = ImageDraw.Draw(frame_image)

            # 先执行正值技能，再执行负值技能（控制技能触发顺序）
            for i in range(6):
                skl = guinfo["info"][guinum[i]]["skl"]
                if skl >= 0:
                    skill_functions[skl](i, frame_index)
            for i in range(6):
                skl = guinfo["info"][guinum[i]]["skl"]
                if skl < 0:
                    skill_functions[skl](i, frame_index)

            #再次确保净化技能的技能收益不小于0
            for i in range(6):
                skl = guinfo["info"][guinum[i]]["skl"]
                if skl == -2:#净化技能
                    if skill_spd[i] < 0:
                        skill_spd[i] = 0

            # 更新各龟位置
            for i in range(6):
                run_positions[i] += (basic_speed[i] + skill_spd[i])

            #绘制跑道线
            for i in range(6):    
                frame_image.paste(img_line.resize((500, 9)), (0, i * 50))
                frame_image.paste(img_line.resize((500, 9)), (0, i * 50 + 41))
            #绘制终点
            top_left = (468, 0)
            bottom_right = (500, 300)
            grid_size = 8  # 每个网格的大小

            # 计算列数和行数
            columns = (bottom_right[0] - top_left[0]) // grid_size
            rows = (bottom_right[1] - top_left[1]) // grid_size

            # 绘制棋盘格
            for row in range(rows):
                for col in range(columns):
                    # 计算当前网格的左上角和右下角
                    x0 = top_left[0] + col * grid_size
                    y0 = top_left[1] + row * grid_size
                    x1 = x0 + grid_size
                    y1 = y0 + grid_size

                    # 交替填充黑白颜色
                    if (row + col) % 2 == 0:
                        draw.rectangle([x0, y0, x1, y1], fill="black")
                    else:
                        draw.rectangle([x0, y0, x1, y1], fill="white")

            # 绘制每条跑道上的龟及相关信息
            for i in range(6):
                turtle_img = Image.open(TURTLE_DIR / f"kame{guinum[i]}.png").convert("RGBA")
                turtle_img_resized = turtle_img.resize((32, 32))
                draw.text((0, i * 50 + 9), guinfo["info"][guinum[i]]["name"], font=setFont, fill="#6f6e63")
                frame_image.paste(turtle_img_resized, (run_positions[i], i * 50 + 9), turtle_img_resized)

            images.append(frame_image)

            # 检查是否有龟到达终点或达到最大帧数
            if any(pos >= 468 for pos in run_positions) or frame_index >= 20:
                break
            frame_index += 1

        # 根据最终位置确定排名及中奖跑道
        draw = ImageDraw.Draw(frame_image)
        currentPos = 1
        winning_lane = None
        colorr = ["#123456", "#cc0000", "#cccc00", "#00cc00", "#00cccc", "#0000cc", "#000000"]
        for pos in range(1500, -1500, -1):
            for j in range(6):
                if run_positions[j] == pos:
                    draw.text((160, j * 50 + 9), "%d位: %.01f%%"%(currentPos, pos / 4.68), font=setFont,
                              fill=colorr[currentPos] if currentPos < len(colorr) else "#000000")
                    if currentPos == 1 and trick_room == 0:
                        winning_lane = j
                    if currentPos == 6 and trick_room == 1:
                        winning_lane = j
                    currentPos += 1
            if currentPos == 7:
                break

        # 为了便于观看，添加几帧静止的最终帧
        for _ in range(7):
            images.append(frame_image)
        gif_path = TURTLE_DIR / "saigui.gif"
        images[0].save(gif_path, save_all=True, append_images=images[1:], optimize=False, duration=100, loop=0)
        await gui.send(MessageSegment.image(gif_path.resolve().as_uri()))

        await asyncio.sleep(1)
        if winning_lane is None or len(m_data["bet"][winning_lane]) == 0:
            await gui.send("此次无人猜中捏")
        else:
            msg = Message("恭喜以下人员猜中：")
            for bettor in m_data["bet"][winning_lane]:
                msg += Message(f"[CQ:at,qq={bettor}]")
            await gui.send(msg)