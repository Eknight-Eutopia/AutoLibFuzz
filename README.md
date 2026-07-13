# Auto Libfuzz

针对 github 中的 lib 库，使用多智能体自动化进行插桩，编译，harness编写，模糊测试过程。

## How to Use

运行以下命令
```shell
uv sync
```

获取 libAFL 源码到 `./externals`
```shell
git clone https://github.com/AFLplusplus/LibAFL.git ./externals/LibAFL
```

按照 `./config/example.config.yaml` 修改配置

复制你想要生成模糊测试工具的 lib 库到 `./target`

运行命令
```shell
uv run main.py -t /path/to/target/lib
```

### Example

以 `libgit2` 为例：
```shell
git clone https://github.com/libgit2/libgit2 ./target/libgit2
uv run main.py -t ./target/libgit2
```
等待运行完成，可以在 `out` 目录（config.yaml中配置项`harness.path`）下看到生成的 harness 源码文件以及编译产物。

## 智能体编排

main agent
- instrument agent
    - terminal tool (execute instrument commands)
    - file tool (read, write)
- harness agent
    - terminal tool (compile harness)
    - file tool (read, write, find)

由主控 agent 控制整个模糊测试流程，根据当前的执行状态进行不同操作。目前设置两个子agent，instrumentor 自动化完成对目标库的代码插桩以及编译工作，生成目标库.a文件，用于后续的harness引用；harness generator则会基于目标库寻找入口点，构写测试用harness。

### 主控 agent

控制整个模糊测试流程。根据当前的状态调用不同的子agent。
初始化时，先调用 `instrumentor`，令其完成对目标库的插桩编译；
插桩完成后，主 agent 调用 `harness generator`，令其对目标库进行分析，寻找入口点，构写测试 harness，（需要编译成功）；
主 agentd 运行 fuzzer 开始模糊测试。

### instrument agent

负责对目标库进行插桩编译：

1. 给其 `README.md` 等内容，查看是否有编译的相关配置
2. 生成并执行编译命令

### harness agent

负责生成可用的 harness：
1. 阅读代码以及文档，寻找目标库可调用的api信息（需要进行预处理缩小范围防止上下文过长）；
2. 基于 LibAFL 对每一个 api 构写 harness 进行测试；

## TODO

- 提高 harness 接口覆盖
- 种子，测试用例生成（llm 分析获取感兴趣的种子）；
- harness 的交互顺序（多组api联合调用，llm分析获取感兴趣的调用顺序）；
- 逻辑漏洞的检验。