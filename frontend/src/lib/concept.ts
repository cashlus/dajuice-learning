export interface KeyElement {
  id: string;
  label: string;
  description: string;
}

export interface ConceptDevelopmentStage {
  id: string;
  period: string;
  stage: string;
  focus: string;
  scholars: string;
  image: string;
  imageAlt: string;
  contribution: string;
}

export const CONCEPT_NAME = "议程设置";
export const CONCEPT_NAME_EN = "Agenda-Setting";

export const KEY_ELEMENTS: KeyElement[] = [
  {
    id: "K1",
    label: "媒体端显著性分配",
    description: "媒体如何赋予议题或对象不同程度的显著性。",
  },
  {
    id: "K2",
    label: "公众端显著性结果",
    description: "公众是否因此认为这些议题或对象更重要。",
  },
  {
    id: "K3",
    label: "转移与因果链路",
    description: "显著性如何从媒体议程转移到公众议程。",
  },
  {
    id: "K4",
    label: "层次区分",
    description: "第一层、第二层与网络议程设置的区别。",
  },
  {
    id: "K5",
    label: "概念边界",
    description: "不等于观点灌输，也不等同于启动效应。",
  },
];

export const CONCEPT_DEVELOPMENT: ConceptDevelopmentStage[] = [
  {
    id: "first-level",
    period: "1972",
    stage: "第一层议程设置",
    focus: "对象显著性",
    scholars: "McCombs & Shaw",
    image: "/history/1972-object-salience.svg",
    imageAlt: "1972 年第一层议程设置的抽象报纸与显著性波纹插画",
    contribution:
      "McCombs 与 Shaw 提出，媒体对对象显著性的分配会转移到公众议程，奠定第一层议程设置。",
  },
  {
    id: "second-level",
    period: "1990s–2000s",
    stage: "第二层议程设置",
    focus: "属性显著性",
    scholars: "Ghanem 等",
    image: "/history/1990s-attribute-salience.svg",
    imageAlt: "1990 年代第二层议程设置的抽象属性标签与透镜插画",
    contribution:
      "研究重心从对象显著性扩展到属性显著性：媒体突出对象的哪些属性，公众也可能更重视这些属性。",
  },
  {
    id: "network-level",
    period: "2011",
    stage: "网络议程设置",
    focus: "关联网络",
    scholars: "Guo & McCombs",
    image: "/history/2011-network-agenda.svg",
    imageAlt: "2011 年网络议程设置的抽象节点与关联网络插画",
    contribution:
      "Guo 与 McCombs 将议程设置推进到第三层，关注媒体中对象与属性之间的关联网络如何转移到公众认知。",
  },
];
