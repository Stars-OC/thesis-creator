# -*- coding: utf-8 -*-
from pathlib import Path
import sys
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from charts.engines.plantuml import _activity_to_dot, _usecase_to_dot


class PlantUMLFallbackTest(unittest.TestCase):
    def test_activity_fallback_keeps_yes_no_edges_and_single_end_node(self):
        dot = _activity_to_dot(
            """
@startuml
start
:提交申请;
if (审核通过?) then (Y)
:生成结果;
else (N)
:退回修改;
endif
stop
@enduml
""".strip()
        )

        self.assertIn("rankdir=TB", dot)
        self.assertIn("Microsoft YaHei", dot)
        self.assertIn("审核通过?", dot)
        self.assertIn("shape=diamond", dot)
        self.assertIn('label="Y"', dot)
        self.assertIn('label="N"', dot)
        self.assertIn("生成结果", dot)
        self.assertIn("退回修改", dot)
        self.assertEqual(1, dot.count('label="结束"'))
        self.assertRegex(dot, r'n\d+ -> n\d+ \[label="Y"\];')
        self.assertRegex(dot, r'n\d+ -> n\d+ \[label="N"\];')

    def test_usecase_fallback_renders_actor_as_person_not_box(self):
        dot = _usecase_to_dot(
            """
@startuml
left to right direction
actor "系统管理员" as SysAdmin
rectangle "在线AI知识库系统" {
    usecase "登录认证" as UC_Login
}
SysAdmin --> UC_Login
@enduml
""".strip()
        )

        self.assertIn("系统管理员", dot)
        self.assertNotIn('SysAdmin [label="系统管理员", shape=box', dot)
        self.assertNotIn('fillcolor="#FFF8E8"', dot)
        self.assertIn("shape=none", dot)
        self.assertIn("SysAdmin -> UC_Login", dot)


if __name__ == "__main__":
    unittest.main()
