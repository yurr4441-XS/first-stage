import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
# 字体问题
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False
# -------------------------
# 1. 手搓一个 DataFrame
# -------------------------
data = {
    "姓名": ["张三", "李四", "王五", "赵六", "小周", "小吴", "小郑", "小钱"],
    "年龄": [21, 22, 20, 23, 24, 21, 22, 23],
    "学习时长": [2.5, 3.0, 1.8, 4.2, 3.5, 2.0, 3.8, 4.5],
    "项目数": [1, 2, 1, 3, 2, 1, 3, 4],
    "成绩": [78, 85, 72, 90, 88, 75, 92, 95],
    "组别": ["A组", "A组", "B组", "B组", "A组", "B组", "A组", "B组"]
}
df = pd.DataFrame(data)
print(df.info())
print(df.describe())
# sns.scatterplot(data=df,x='学习时长',y='成绩',hue='组别')
# plt.show()
sns.barplot(data=df,x='姓名',y='项目数',hue='组别')
plt.title('嘿嘿嗨：项目数')
plt.show()
sns.histplot(data=df,x='成绩',hue='组别',kde=True)
plt.show()
sns.boxplot(data=df,x='组别',hue='成绩')
plt.show()
# plotly 散点图
fig = px.scatter(df, x="学习时长", y="成绩", color="组别",
                 hover_data=["姓名", "项目数"],
                 title="plotly散点图：学习时长与成绩")
fig.show()

# plotly 柱状图
fig = px.bar(df, x="姓名", y="项目数", color="组别",
             title="plotly柱状图：每个人的项目数")
fig.show()

# plotly 直方图
fig = px.histogram(df, x="成绩", color="组别",
                   title="plotly直方图：成绩分布")
fig.show()

# plotly 折线图
fig = px.line(df.sort_values("学习时长"),
              x="学习时长", y="成绩", color="组别",
              markers=True,
              title="plotly折线图：学习时长与成绩变化")
fig.show()













