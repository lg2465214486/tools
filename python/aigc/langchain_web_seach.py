import os
import time
from abc import ABC

from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from typing import Any, List, Optional, Dict, Iterator, Generator
import requests
import json
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate

"""
回答系统提示词
"""
SYSTEM_CHAIN_PROMPT = """
你是一个专业的AI研究助手，擅长深度网络搜索和信息综合分析。

# 核心能力
- 理解复杂问题的深层需求
- 规划多步骤搜索策略
- 综合分析不同来源的信息
- 提供有深度、有依据的答案

# 输出要求
- 使用中文回答
- 结构清晰，分点论述
- 如信息不足或存在矛盾，需明确指出
- 避免主观臆断，基于事实分析
"""

"""
分析问题提示词
"""
QUESTION_ANALYZER_CHAIN_SYSTEM_CHAIN = """
# 角色：研究分析专家
您是一位资深研究分析师，擅长深度解构用户问题，识别核心研究需求，规划清晰的调研路径

## 核心能力
- 批判性思维与概念分析
- 问题拆解与框架构建  
- 研究方法设计

## 输出规范
请严格按以下JSON格式输出分析结果：
    "core_question": "问题本质的精炼表述",
    "sub_questions": [
        "需要优先解答的子问题1",
        "需要优先解答的子问题2",
        "需要优先解答的子问题3"
    ],
    "key_concepts": [
        "需要明确定义的核心概念1",
        "需要明确定义的核心概念2"
    ],
    "search_focus": [
        "重点调研方向1",
        "重点调研方向2"
    ]
"""

QUESTION_ANALYZER_CHAIN_HUMAN_CHAIN = """
请分析以下问题：

{question}
"""

"""
搜索策略生成提示词
"""
STRATEGY_HUMAN_CHAIN_PROMPT = """
## 问题分析
{analysis_result}

## 任务
基于问题分析，设计三轮搜索策略：

## 输出要求
请严格按照以下JSON格式输出：

{{
    "search_rounds": [
        {{
            "round": 1,
            "purpose": "第一轮搜索的目的",
            "search_text": "搜索词条",
            "expected_info": "期望获取的信息类型"
        }},
        {{
            "round": 2, 
            "purpose": "第二轮搜索的目的",
            "search_text": "搜索词条",
            "expected_info": "期望获取的信息类型"
        }},
        {{
            "round": 3,
            "purpose": "第三轮搜索的目的", 
            "search_text": "搜索词条",
            "expected_info": "期望获取的信息类型"
        }}
    ]
}}
"""

"""
整理和清洗搜索数据提示词
"""
ORGANIZER_CHAIN_HUMAN_PROMPT = """
## 角色
你是信息整理专家，负责从搜索结果中提取和整理有价值的信息。

## 用户问题
{question}

## 搜索到的原始信息
{search_results}

## 你的任务
仔细阅读所有搜索结果，提取关键信息并分类整理。重点保留具体细节和数据，不要过度概括。

## 根据问题类型灵活调整
- **技术问题**：侧重具体配置、步骤、参数
- **商业分析**：侧重数据、趋势、竞争信息  
- **生活建议**：侧重实用方法、注意事项
- **学术研究**：侧重理论、证据、不同观点
- **产品比较**：侧重具体差异、优缺点

## 整理原则
1. **保留细节**：保持具体的数字、名称、时间、地点等关键信息
2. **分类合理**：根据问题类型自动调整分类逻辑
3. **标注来源**：每个信息都要注明出处和可信度
4. **避免过度提炼**：不要为了简洁而丢失重要细节

## 通用分类框架
请根据问题性质，使用一下结构进行输出：
{{
    "organized_info": {{
        "core_facts": [
            {{
                "fact": "具体的事实描述，保留原始细节",
                "context": "事实的背景或上下文",
                "source": "来源信息",
                "url": "来源链接",
                "reliability": "高/中/低",
                "timestamp": "信息时间（如有）"
            }}
        ],
        "key_data_points": [
            {{
                "data_description": "数据的具体含义",
                "value": "具体的数值或内容",
                "unit": "单位（如有）",
                "timeframe": "数据对应的时间范围",
                "source": "来源信息",
                "url": "来源链接",
                "significance": "这个数据的重要性"
            }}
        ],
        "practical_details": [
            {{
                "category": "信息类别（如步骤、方法、配置等）",
                "specific_content": "具体的内容描述，保留操作细节",
                "applicability": "适用条件或场景",
                "source": "来源信息",
                "url": "来源链接"
            }}
        ],
        "expert_insights": [
            {{
                "viewpoint": "具体的观点或分析",
                "supporting_evidence": "支撑该观点的证据",
                "expert_background": "专家背景（如有）",
                "source": "来源信息",
                "url": "来源链接",
                "credibility": "可信度评估"
            }}
        ],
        "comparative_info": [
            {{
                "comparison_aspect": "比较的维度",
                "option_a": "选项A的具体信息",
                "option_b": "选项B的具体信息",
                "differences": "具体的差异点",
                "source": "来源信息",
                "url": "来源链接"
            }}
        ],
        "actionable_advice": [
            {{
                "advice_type": "建议类型",
                "concrete_steps": "具体的步骤或方法",
                "expected_outcome": "预期结果",
                "precautions": "注意事项",
                "source": "来源信息",
                "url": "来源链接"
            }}
        ]
    }}
}}
"""

"""
深度思考提示词
"""
DEEP_ANALYZER_CHAIN_PROMPT = """
## 角色
你是思考深入的行业观察者，善于从具体信息中发现有价值的模式和洞察。

## 分析基础
研究问题: {question}

整理后的具体信息:
{organized_data}

## 你的任务
基于这些具体信息，进行深度思考和分析。重点不是重复事实，而是发现：
- 信息之间的关联和模式
- 现象背后的原因和逻辑  
- 可能的发展趋势和影响
- 对用户有实际价值的洞察

## 分析维度（根据信息类型选择重点）

### 如果信息偏向事实数据：
- 这些数据说明了什么趋势或模式？
- 不同数据点之间有什么关联？
- 这些数据的实际意义是什么？

### 如果信息偏向方法步骤：
- 这些方法背后的原理是什么？
- 不同方法的优缺点和适用场景？
- 执行时可能遇到什么挑战？

### 如果信息偏向观点分析：
- 不同观点之间的共识和分歧在哪里？
- 这些观点背后的假设和依据？
- 哪些观点更有说服力，为什么？

### 如果信息偏向比较选择：
- 各选项的核心差异和权衡点？
- 选择时最应该考虑的因素？
- 长期来看哪个选择更有优势？

## 输出要求
请生成有深度的分析，包含：

{{
    "analysis_insights": {{
        "pattern_observations": [
            "基于具体信息观察到的模式或趋势",
            "信息之间有趣的关联性"
        ],
        "underlying_factors": [
            "现象背后的可能原因",
            "驱动这些发展的关键因素"
        ],
        "practical_implications": [
            "这些信息对用户的实际意义",
            "可能产生的影响或后果"
        ],
        "forward_looking_views": [
            "基于现状的合理推测",
            "值得关注的发展方向"
        ],
        "critical_considerations": [
            "需要警惕的方面或潜在风险",
            "信息的局限性或不确定性"
        ]
    }}
}}

## 特别提醒
- 每个洞察都要基于前面整理的具体信息
- 避免空泛的结论，要有具体的支撑点
- 可以有自己的推理，但要标明是分析推断
- 用平实的语言表达深度思考
"""

"""
总结回答提示词
"""
REPORT_GENERATOR_CHAIN_HUMAN_PROMPT = """
用户输入的内容：
{question}

网络调研发现的结果：
{analysis_result}

深度洞察后的结果：
{deep_analysis}

请围绕用户输入的内容，结合网络调研发现的结果以及深度洞察后的结果来回答用户

# 文末格式化标注来源信息和网页链接，格式如下：
**参考资料**
[网页1标题](网页1链接地址)
[网页2标题](网页2链接地址)
[网页3标题](网页3链接地址)
......
参考资料不要胡编乱造，要填写{{analysis_result}}中的真实信息，如果没有就不要填
"""


class BaiduApi:
    """百度搜索API封装类"""

    """api_key 可在官网申请"""
    api_key: str = ''

    def web_search(self, query):
        """执行百度网页搜索"""
        url = "https://qianfan.baidubce.com/v2/ai_search/web_search"

        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": query
                }
            ],
            "edition": "standard",
            "search_source": "baidu_search_v2",
            "search_recency_filter": "week"
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        # 发送POST请求到百度搜索API
        response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
        return response.json()


def md2json(content):
    """将markdown格式的JSON字符串转换为Python字典"""
    content = content.lstrip("```json")  # 去除开头的```json标记
    content = content.rstrip("```")  # 去除结尾的```标记
    return json.loads(content)  # 解析JSON字符串


class DeepSeekChatModel(BaseChatModel, ABC):
    """兼容 LangChain Expression Language (LCEL) 的 DeepSeek Chat 模型"""

    api_key: str
    model_name: str = "deepseek-chat"  # 模型名称
    api_url: str = "https://api.deepseek.com/v1/chat/completions"  # API地址
    temperature: float = 0.7  # 生成温度参数
    timeout: int = 3000  # 请求超时时间

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """将 LangChain 的 Message 对象转换为 DeepSeek 所需格式"""
        result = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"  # 用户消息
            elif isinstance(msg, AIMessage):
                role = "assistant"  # AI助手消息
            elif isinstance(msg, SystemMessage):
                role = "system"  # 系统消息
            else:
                role = "user"  # 默认用户消息
            result.append({"role": role, "content": msg.content})
        return result

    # --- 流式调用 ---
    def _stream(
            self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any
    ) -> Generator[ChatGenerationChunk, None, None]:
        """流式返回 ChatGenerationChunk"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
            "stream": True  # 开启流式输出
        }

        # 发送流式请求
        with requests.post(
                self.api_url, headers=headers, json=payload, stream=True, timeout=self.timeout
        ) as response:
            if response.status_code != 200:
                raise ValueError(f"DeepSeek 流式接口错误: {response.status_code} - {response.text}")

            # 处理流式响应
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith(b"data: "):
                    data = line[len(b"data: "):].decode("utf-8")
                    if data.strip() == "[DONE]":  # 流式结束标记
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            text = delta["content"]
                            yield ChatGenerationChunk(
                                message=AIMessageChunk(content=text)
                            )
                    except Exception:
                        continue

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any) -> ChatResult:
        """核心调用逻辑 - 生成聊天响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
        }

        # 发送API请求
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=self.timeout)
        if response.status_code != 200:
            raise ValueError(f"DeepSeek API 调用失败: {response.status_code} - {response.text}")

        # 解析响应数据
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # 处理停止词
        if stop:
            for s in stop:
                content = content.split(s)[0]

        # 返回符合 LangChain 核心结构的 ChatResult
        gen = ChatGeneration(message=AIMessage(content=content))
        return ChatResult(generations=[gen])

    @property
    def _llm_type(self) -> str:
        """返回LLM类型标识"""
        return "deepseek-chat-lcel"

    @property
    def _identifying_params(self) -> dict:
        """返回模型识别参数"""
        return {
            "model_name": self.model_name,
            "api_url": self.api_url,
            "temperature": self.temperature,
        }


class DeepWebSearchChinese:
    """中文深度网络搜索器 - 主类"""

    def __init__(self):
        # 初始化DeepSeek模型和百度搜索API
        self.llmModel = DeepSeekChatModel(api_key="") ## api_key可在官网申请
        self.search = BaiduApi()

    def web_search(self, query):
        """执行网络搜索并优化结果"""
        print(f"🔍 执行搜索: {query}")
        try:
            answer = self.search.web_search(query)
            return answer
        except Exception as e:
            return f"搜索执行错误: {str(e)}"

    def question_analyzer_chain(self, question):
        """问题分析链 - 解析用户问题"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", QUESTION_ANALYZER_CHAIN_SYSTEM_CHAIN),
                ("human", QUESTION_ANALYZER_CHAIN_HUMAN_CHAIN),
            ]
        )
        ## LCEL写法创建chain
        chain = (
                prompt
                | self.llmModel
                | StrOutputParser()
        )
        return chain.invoke({"question": question})

    def strategy_human_chain(self, analyzer):
        """搜索策略生成链 - 制定搜索计划"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_CHAIN_PROMPT),
                ("human", STRATEGY_HUMAN_CHAIN_PROMPT),
            ]
        )
        ## LCEL写法创建chain
        chain = (
                prompt
                | self.llmModel
                | StrOutputParser()
        )
        return chain.invoke({"analysis_result": analyzer})

    def organizer_chain(self, question, search_results):
        """数据整理链 - 清洗和组织搜索结果"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", ORGANIZER_CHAIN_HUMAN_PROMPT),
                ("human", "请开始整理数据"),
            ]
        )
        ## LCEL写法创建chain
        chain = (
                prompt
                | self.llmModel
                | StrOutputParser()
        )
        return chain.invoke({"question": question, "search_results": search_results})

    def deep_analyzer_chain(self, question, organized_data):
        """深度分析链 - 对整理后的数据进行深入分析"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", DEEP_ANALYZER_CHAIN_PROMPT),
                ("human", "请开始深度分析"),
            ]
        )
        ## LCEL写法创建chain
        chain = (
                prompt
                | self.llmModel
                | StrOutputParser()
        )
        return chain.invoke({"question": question, "organized_data": organized_data})

    def report_generator_chain(self, question, analysis_result, deep_analysis):
        """报告生成链 - 生成最终回答报告"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_CHAIN_PROMPT),
                ("human", REPORT_GENERATOR_CHAIN_HUMAN_PROMPT),
            ]
        )
        ## LCEL写法创建chain
        chain = (
                prompt
                | self.llmModel
                | StrOutputParser()
        )
        return chain.invoke({"question": question, "analysis_result": analysis_result, "deep_analysis": deep_analysis})

    def search_chain(self, strategy_result):
        """执行搜索链 - 根据策略执行多轮搜索"""
        search_content = []
        # 遍历每一轮搜索策略
        for search_rounds in strategy_result['search_rounds']:
            print(f"真正进行第{search_rounds['round']}轮搜索")
            # 执行搜索
            res = self.search.web_search(search_rounds['search_text'])
            # 处理搜索结果
            for references in res['references']:
                print(references)
                search_content.append({
                    'url': references['url'],  # 网页URL
                    'title': references['title'],  # 网页标题
                    'content': references['content']  # 网页内容
                })
        return search_content

    def main_chain(self, question):
        """主执行链 - 协调整个搜索分析流程"""
        print(f"{'=' * 80}\n分析问题\n{'=' * 80}\n")
        analyzer_result = self.question_analyzer_chain(question)
        print(analyzer_result)

        print(f"{'=' * 80}\n搜索策略生成\n{'=' * 80}\n")
        strategy_result = self.strategy_human_chain(md2json(analyzer_result))
        print(strategy_result)

        print(f"{'=' * 80}\n开始搜索\n{'=' * 80}\n")
        search_result = self.search_chain(md2json(strategy_result))
        print(search_result)

        print(f"{'=' * 80}\n开始整理和清洗搜索数据\n{'=' * 80}\n")
        organizer_result = self.organizer_chain(question, search_result)
        print(organizer_result)

        print(f"{'=' * 80}\n开始深度分析\n{'=' * 80}\n")
        deep_analyzer_result = self.deep_analyzer_chain(question, organizer_result)
        print(deep_analyzer_result)

        print(f"{'=' * 80}\n构建结果\n{'=' * 80}\n")
        final_report = self.report_generator_chain(question, organizer_result, deep_analyzer_result)
        print(final_report)
        return final_report


if __name__ == '__main__':
    # 初始化深度搜索器
    searcher = DeepWebSearchChinese()

    question = "给我一份当前去北方旅游的计划"
    searcher.main_chain(question)
