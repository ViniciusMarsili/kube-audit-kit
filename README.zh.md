[English](README.md) | [中文](README.zh.md)

# Kube Audit Kit

> **Kube Audit Kit** 是一个 [Claude Code Skill](https://code.claude.com/docs/en/skills)，用于对 Kubernetes 集群进行零侵入的安全审计。

Kube Audit Kit 可以导出指定 Context/Namespace 下的所有资源，进行深度清洗、智能应用分组，并基于如下多项行业标准生成全面的安全审计报告。

- [Pod Security Standards (PSS)](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [NSA Kubernetes Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)
- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)

---

## 特性

- **零侵入**: 仅执行 `get/list` 操作，**不修改**集群任何状态
- **全覆盖**: 动态发现所有资源类型，非硬编码列表
- **智能分组**: 基于 Workload 拓扑自动关联应用资源
- **双重审计**: 脚本静态扫描 + AI 专家深度分析
- **类型安全**: 完整的 Python 类型注解
- **美观输出**: 使用 Rich 库提供彩色控制台输出

## 安全检查覆盖

### 🛡️ Pod Security（基于 PSS/NSA）

基于 [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/) 和 [NSA Kubernetes Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)

| 检查项         | 说明                                          |
| :------------- | :-------------------------------------------- |
| 特权模式       | 检测 `privileged: true`                       |
| 宿主机命名空间 | 检测 `hostNetwork`、`hostPID`、`hostIPC`      |
| 能力           | 检测危险 capabilities 添加/删除               |
| 安全上下文     | 检测 `runAsNonRoot`、`readOnlyRootFilesystem` |
| 资源限制       | 检测 CPU/内存 requests 和 limits              |
| 健康检查       | 检测 liveness/readiness/startup probes        |
| 镜像安全       | 检测 `:latest` 标签                           |

### 🔐 RBAC 权限审计

基于 [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes) 和 [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

| 检查项     | 说明                                  |
| :--------- | :------------------------------------ |
| 通配符检测 | 检测 `*` in verbs/resources/apiGroups |
| 高权限角色 | 检测 cluster-admin、admin、edit、view |
| 过度授权   | 分析 Role/ClusterRole 规则合理性      |

### 🌐 网络安全审计

基于 [NSA Network Policy Guidelines](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/) 和 [CIS NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

| 检查项        | 说明                                   |
| :------------ | :------------------------------------- |
| NetworkPolicy | 检测命名空间是否有网络策略保护         |
| Service 暴露  | 检测 LoadBalancer/NodePort/externalIPs |
| Ingress 配置  | 检测 TLS 配置和外部暴露的 hosts        |

### 💾 宿主机挂载检测

基于 [CIS Kubernetes Benchmark 5.2.3](https://www.cisecurity.org/benchmark/kubernetes) 和 [NSA Guidelines Section 3.3](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/)

| 检查项   | 说明                                       |
| :------- | :----------------------------------------- |
| hostPath | 检测宿主机路径挂载                         |
| 危险路径 | 识别 docker.sock、/etc、/root 等高风险路径 |
| 风险分级 | 按 Critical/Warning 分级评估               |

### 🛡️ 安全策略检查

基于 [Kubernetes seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/) 和 [AppArmor Documentation](https://kubernetes.io/docs/tutorials/clusters/apparmor/)

| 检查项   | 说明                         |
| :------- | :--------------------------- |
| seccomp  | 检测 seccompProfile 配置状态 |
| AppArmor | 检测 AppArmor 注解配置       |

### 🔄 高可用性配置

基于 [Kubernetes PodDisruptionBudget](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/) 和 [CIS Benchmark 5.2.9](https://www.cisecurity.org/benchmark/kubernetes)

| 检查项              | 说明                                   |
| :------------------ | :------------------------------------- |
| PodDisruptionBudget | 检测 PDB 配置                          |
| Secret 类型         | 检测 Secret 类型是否合适               |
| ServiceAccount      | 检测 automountServiceAccountToken 配置 |

### 🔍 敏感信息扫描

基于 [NSA Guidelines Section 4.2](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/2716980/nsa-cisa-publish-guidance-on-how-to-protect-kubernetes-clusters/) 和 [CIS Benchmark Secret Management](https://www.cisecurity.org/benchmark/kubernetes)

| 检查项         | 说明                           |
| :------------- | :----------------------------- |
| ConfigMap 扫描 | 检测敏感关键词和高熵字符串     |
| Secret 分析    | 检测非敏感信息误用             |
| 使用方式区分   | 区分 Volume 挂载和 EnvVar 引用 |

---

## 安装

### 方式一：作为 Personal Skill 安装（推荐）

将 Skill 安装到个人目录，在所有项目中可用：

```bash
git clone https://github.com/crazygit/kube-audit-kit.git ~/.claude/skills/kube-audit-kit
```

### 方式二：作为 Project Skill 安装

将 Skill 安装到特定项目，仅对该项目可用：

```bash
git clone https://github.com/crazygit/kube-audit-kit.git .claude/skills/kube-audit-kit
```

### 安装后

验证 Skill 是否已加载，可以使用以下任一方式：

**方式一：使用 /skills 命令**

```
/skills
```

**方式二：询问 Claude**

```
What Skills are available?
```

如果 `kube-audit-kit` 出现在列表中，说明 Skill 已成功加载。

> **注意**: 最新版本的 Claude Code 客户端支持自动热加载，通常无需重启。如果 Skill 未出现在列表中，请尝试重启 Claude Code。

---

## 使用

安装后通常无需重启。如未生效，请重启 Claude Code。

### 触发 Skill

根据 SKILL.md 中的定义，你可以用以下方式触发 Skill：

```
"审计生产环境 prod-cluster 的 backend 命名空间"
"检查 staging 环境 staging-cluster 的 payment 服务"
"分析开发环境 dev-cluster 的所有应用配置"
```

或者使用更通用的表述：

```
"请审计 my-context 的 my-namespace 命名空间"
"帮我检查 cluster-1 环境"
```

Claude 会识别到你的意图并自动使用 `kube-audit-kit` Skill，然后提示你输入 Context 和 Namespace 参数。

### 完整工作流程

Skill 执行以下步骤：

1. **导出资源** - 使用 `kubectl get/list` 导出所有资源类型
2. **清洗资源** - 移除状态字段和元数据噪声
3. **分组应用** - 基于 Workload 拓扑智能关联资源
4. **安全审计** - 静态分析 + AI 深度分析生成报告

### 环境要求

| 组件    | 版本要求                   |
| :------ | :------------------------- |
| Python  | >= 3.14                    |
| kubectl | 任意版本（需配置目标集群） |
| uv      | 最新版本（依赖管理）       |

### 手动执行脚本

如果你想直接运行脚本而不通过 Skill：

```bash
# 安装依赖
uv sync

# 执行审计流程
CTX=your-context
NS=your-namespace

uv run python scripts/export.py --context $CTX --namespace $NS
uv run python scripts/sanitize.py --context $CTX --namespace $NS
uv run python scripts/group_apps.py --context $CTX --namespace $NS
uv run python scripts/audit.py --context $CTX --namespace $NS
```

---

## 安全建议

### 🔐 使用专用审计账户

建议创建专用的服务账户并通过 RBAC 严格控制权限。如果你担心审计过程暴露敏感的 Secret 数据，可以不授予 Secret 权限，此时其他资源的检查仍然可以正常进行。

项目提供了审计服务账户配置示例：

```bash
# 查看示例配置
cat examples/audit-service-account.yaml

# 应用到目标命名空间（请先根据实际情况修改 Namespace）
kubectl apply -f examples/audit-service-account.yaml

# 获取审计账户 token（有效期 1 小时）
kubectl -n <namespace> create token audit-service-account --duration=1h

# 配置 kubeconfig 使用新的审计 Context
kubectl config set-credentials audit-service-account --token=<token>
kubectl config set-context audit-context \
  --cluster=<your-cluster> \
  --user=audit-service-account \
  --namespace=<target-namespace>
```

**权限说明**：

| 权限                          | 是否必需 | 说明                           |
| :---------------------------- | :------- | :----------------------------- |
| Pod/Deployment/Workload       | ✅ 必需  | 工作负载安全检查               |
| ConfigMap                     | ✅ 必需  | 敏感信息扫描                   |
| Service/Ingress/NetworkPolicy | ✅ 必需  | 网络安全审计                   |
| RBAC 资源                     | ✅ 必需  | RBAC 权限审计                  |
| **Secret**                    | ⚪ 可选  | 如不授权，跳过 Secret 相关检查 |

**无 Secret 权限时的影响**：

- ❌ 无法执行 Secret 类型检查
- ❌ 无法检测 Secret 中的非敏感信息误用
- ✅ 其他所有检查项正常工作（Pod Security、RBAC、网络、hostPath 等）

**安全最佳实践**：

- ✅ 最小权限原则 - 仅授予审计所需的最低权限
- ✅ Secret 可选 - 根据安全策略决定是否授予 Secret 权限
- ✅ 命名空间隔离 - 使用 Role 限制在特定命名空间
- ✅ 定期轮换 - 定期更新服务账户的 token
- ✅ 审计日志 - 启用 Kubernetes 审计日志追踪审计活动

---

## 文档结构

```
kube-audit-kit/
├── SKILL.md                      # Skill 主文件（包含元数据和指令）
├── CLAUDE.md                     # 项目级 Claude 指令
├── README.md                     # 英文文档
├── README.zh.md                  # 中文文档
├── pyproject.toml                # Python 项目配置
├── examples/
│   └── audit-service-account.yaml # 审计服务账户 RBAC 配置示例
├── scripts/
│   ├── export.py                 # 导出 Kubernetes 资源
│   ├── sanitize.py               # 清洗 YAML 文件
│   ├── group_apps.py             # 智能应用分组
│   ├── audit.py                  # 安全审计
│   └── utils.py                  # 工具函数
├── tests/                        # 测试文件
└── output/                       # 审计输出目录（运行后生成）
```

---

## 输出结果

审计完成后，报告位于**你的当前工作目录** `output/{context}/{namespace}/audit/`：

```
output/{context}/{namespace}/audit/
├── audit_results.json           # 结构化审计结果（包含所有检查项）
├── configmap_to_secret.csv      # ConfigMap 敏感信息
├── secret_to_configmap.csv      # Secret 非敏感信息
├── rbac_issues.csv              # RBAC 权限审计结果
├── network_security.csv         # 网络安全审计结果
├── hostpath_mounts.csv          # 宿主机挂载检测结果
├── security_policies.csv        # seccomp/AppArmor 检查结果
├── pdb_and_secrets.csv          # PDB/Secret/ServiceAccount 检查结果
└── audit_report.md              # 完整审计报告（由 AI 生成）
```

> **注意**: 输出目录创建在**你的工作目录**（调用 SKILL 时的目录），而不是 SKILL 安装目录。这是通过 SKILL.md 中设置的 `KUBE_AUDIT_OUTPUT` 环境变量实现的。

---

## 常见问题

### Skill 不触发？

确保描述中包含的关键词与你的请求匹配。尝试使用更明确的表述：

```
"请对 Kubernetes 资源进行安全审计"
"帮我审计 production Namespace"
```

### Context 或 Namespace 找不到？

```bash
# 查看可用的 Contexts
kubectl config get-contexts

# 查看目标 Context 下的 Namespaces
kubectl get namespaces --context <your-context>
```

---

## 安全提醒

> ⚠️ **重要**: `output/` 目录包含 Secret 数据，请审计完成后及时安全删除！

```bash
# 审计完成后，安全删除输出目录
rm -rf output/<context>/<namespace>
```

---

## 许可证

MIT License

---

## 相关链接

- [Claude Code Skills 文档](https://code.claude.com/docs/en/skills)
- [Agent Skills 最佳实践](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices)
- [GitHub 项目](https://github.com/crazygit/kube-audit-kit)
