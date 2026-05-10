import type { DropdownProps } from 'antd';
import { Dropdown } from 'antd';
import React from 'react';

/**
 * 与 Ant Design Pro 模板一致的顶栏下拉容器（简化版，无 antd-style 依赖）。
 */
const HeaderDropdown: React.FC<DropdownProps> = ({ overlayClassName: _cls, ...props }) => (
  <Dropdown placement="bottomRight" overlayStyle={{ zIndex: 1050 }} {...props} />
);

export default HeaderDropdown;
