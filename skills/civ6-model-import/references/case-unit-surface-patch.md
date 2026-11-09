# 单位曲面贴片：从方形面片到轮廓网

单位材质的参数表里没有 `Opacity`，轮廓只能由几何给出。本案例记录女漂右手声痕从「43 面方形面片加整张带星图」改成「4103 面星形三角网加同图」的全过程，含三次错位的成因与对应判据。

## 一、前置判定：参照工程属于哪条链

照搬领袖工程之前先确认材质类的参数表。

| 工程 | `m_ClassName` | 参数数 | 关键参数 |
|---|---|---|---|
| 御三家 `MI_3XingStar.mtl:23` | `Leader_Matte` | 2 | `BaseColor` 1024² RGBA（星芒贴花按自身类别出图，不套用领袖基色自适应档位）、`Opacity` 256² `PF_R8_UNORM`（`Leader_OPAC`） |
| 女漂 `MI_3XingStar.mtl:65` | `Unit` | 11 | `AO`、`BaseColor`、`Emissive`、`Emissive_Minimum_Weight`、`Gloss`、`Metalness`、`Normal`、`Seperate_AO_UV`、`TintMask`、`Translucency`、`UV_ScrollRate` |

单位链的 11 项里没有 `Opacity`。硬塞 `Leader_Matte` 与 `Generic_OPAC` 会被 cook 拒绝，原文两条：

```
Entity: 'MI_3XingStar' has class: 'Leader_Matte', but is bound to parameter: 'Material' which does not accept this class.
Entity: 'T_3XingStar_Alpha' has class: 'Generic_OPAC', but is bound to parameter: 'Opacity' which does not accept this class.
```

**结论**：领袖侧那张 256² 掩膜在单位链上没有消费方。想让单位上的贴片呈星形，轮廓必须写进几何。

## 二、形状重建的坐标约定

原面片是 43 个矩形面，UV 压在整张带星图的范围上，轮廓由贴图 alpha 决定。重建分四步。

1. 取原面片每条环的 UV 与位置，最小二乘拟合 `pos = c0 + c1·u + c2·v` 平面。
2. 按拟合平面与蒙版 alpha 生成 `res × res` 栅格，只保留蒙版不透明的格子。
3. 每格四角按平面求位置，沿面片外法线偏移 `outward`，写成两三角。
4. 新顶点按最近源环继承原顶点的 vertex group 权重，UV 写回该格四角。

外法线由原面片法线求和得到，方向用「面片质心减去全身质心」校正指向体外。

## 三、三次错位与对应判据

| 错位形态 | 成因 | 判据 |
|---|---|---|
| 贴片落到裙摆上 | 平面拟合在网格尚未缩放成米制时做，残差 0.2185 厘米，投影落进相邻 UV 岛 | 拟合必须在缩放之后，残差小于 0.01 厘米（缩放后实测 0.0013 / 0.0016 厘米） |
| 贴片整体悬在体外 | 朝外偏移参数按厘米给成 `0.30`，米制网格上是 30 厘米 | 偏移单位与网格一致，米制取 0.0015；同时断言质心漂移小于允许值 |
| 贴片在摆姿势时飞到别处 | 重建顶点不带任何 vertex group，权重为空即脱离骨链 | 断言继承权重的顶点数等于新建顶点数 |

三条判据都写在 `scripts/unit/patch_shape_rebuild.py` 的断言里，任何一条不满足即退出码非零。

## 四、实证读数

| 项 | 女漂 | 男漂 |
|---|---|---|
| 面数 | 43 → 4103 | 22 → 3314 |
| 拟合残差 | 0.0013 厘米 | 0.0016 厘米 |
| 质心漂移 | 0.002 厘米 | 0.002 厘米 |
| 净空下限 | 0.1355 厘米 | — |
| 主导骨分布 | `Bip001RHand` 9035 / `Bip001RForeTwist1` 3274 | 9160 / 782 |
| 骨点到贴片质心 | 1.18 / 11.04 厘米 | 1.94 / 12.07 厘米 |

两侧主导骨结构一致，贴片随 `Bip001RHand` 所在骨链运动，实机待机不再脱离右手。

## 五、父级位移的写法

在 Blender 里并排摆放多个模型时，位移只加在骨架上。网格是骨架的子级，各自再位移一次会叠成两倍，表现为贴片远离手掌。判据是贴片质心到 `Bip001RHand` 骨点的距离，应稳定落在 1~2 厘米。
