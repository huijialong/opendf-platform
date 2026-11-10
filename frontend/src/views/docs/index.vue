<script setup>
const manual = [
  {
    title: '1. 登记设备',
    body: '打开采集模块 → 设备登记。硬件类型包括 Stanford UMI 手持夹爪、Pico VR、第一视角相机和 Piper/Franka 机械臂。标定内参以 JSON 存在设备上，例如 fx、fy、cx、cy。',
  },
  {
    title: '2. 创建任务',
    body: '在任务管理里新建任务，选择场景（机械臂抓取、VR 第一视角、触觉作业、工业巡检等），指定负责人和目标样本数。进度按已入库会话数除以目标样本计算。',
  },
  {
    title: '3. 采集或生成样本',
    body: '采集会话页可以拖入 mp4 视频和 json/csv 轨迹。没有机械臂时，点击「生成模拟样本」。后端会写出 10 秒、30Hz 的正弦末端轨迹，夹爪在 3.0 到 7.0 秒闭合，并渲染一段对齐的测试视频。',
  },
  {
    title: '4. 时间轴标注',
    body: '标注工作台上方是视频，下方 Canvas 同时绘制末端速度（橙色）和夹爪开合（蓝色）。红色游标跟视频 currentTime 同步。点击波形跳转，拖拽超过 0.3 秒后选择 Approach、Grasp 或 Place。空格键播放，左右方向键每次 0.1 秒。',
  },
  {
    title: '5. 审核',
    body: '审核模块按切片给出通过或驳回。驳回必须填写可定位的原因。一个会话的全部分片都通过后，会话标记为已审核，任务进入已归档。',
  },
  {
    title: '6. 导出',
    body: '数据模块选择任务和格式。LeRobot v2.1 包包含 meta/info.json、episodes.jsonl、tasks.jsonl、stats，以及 data/chunk-000/episode_*.parquet；有视频时写入 videos/chunk-000/observation.images.rgb/。HDF5 结构包按 observations / actions / timestamps 组路径组织；JSON 包是可读索引。下载链接指向 /storage/export。',
  },
]

const standard = [
  {
    title: '坐标系与单位',
    body: 'ee_pose 为 [x, y, z, rx, ry, rz]，位置单位米，姿态为弧度。gripper_width 为夹爪开口宽度，单位米，示例里张开约 0.08，闭合约 0.01。velocity 为末端速度标量。默认采样 30Hz。',
  },
  {
    title: '动作字典',
    body: 'APPROACH 接近目标；GRASP 夹爪闭合抓住物体；LIFT 提起；MOVE 搬运；PLACE 放置并张开。单帧事件 Collision、Slip、Success 记在切片备注里。时间使用秒，保留 3 位小数，同时给出 30fps 下的起止帧。',
  },
  {
    title: '会话元数据',
    body: '每条 CaptureSession 有 session_uuid、task_id、device_sn、video_filename、trajectory_filename、duration_seconds、frame_count。视频和轨迹放在 storage/raw，通过 /storage/raw/<filename> 访问。',
  },
  {
    title: '双域与导出',
    body: 'origin 保存原始轨迹 JSON 和视频。std 是对齐后的表：timestamp、frame_idx、末端 6 维、gripper_width、velocity、action_label。LeRobot info.json 声明 fps、robot_type 和 feature shape。审核未通过的切片仍会写入 annotations/，review_status 字段保留结论。',
  },
]
</script>

<template>
  <div>
    <div class="page-head">
      <div>
        <h2>操作手册</h2>
        <p>采集、标注、审核和导出的操作说明，以及时间轴与数据包的 STD 约定。</p>
      </div>
    </div>
    <section class="odf-card block">
      <el-tabs>
        <el-tab-pane label="操作手册">
          <article v-for="item in manual" :key="item.title" class="doc">
            <h3>{{ item.title }}</h3>
            <p>{{ item.body }}</p>
          </article>
        </el-tab-pane>
        <el-tab-pane label="STD 手册">
          <article v-for="item in standard" :key="item.title" class="doc">
            <h3>{{ item.title }}</h3>
            <p>{{ item.body }}</p>
          </article>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<style scoped>
.block { padding: 8px 20px 20px; }
.doc { padding: 8px 0 4px; border-bottom: 1px solid #f0f2f5; }
.doc h3 { margin: 8px 0; font-size: 16px; }
.doc p { margin: 0 0 12px; color: #606266; line-height: 1.7; }
</style>
