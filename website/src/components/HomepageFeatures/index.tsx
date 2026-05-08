import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  Svg: React.ComponentType<React.ComponentProps<'svg'>>;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: '控制面与 Agent 分离',
    Svg: require('@site/static/img/undraw_docusaurus_mountain.svg').default,
    description: (
      <>
        HTTP API、gRPC 与元数据在控制面；边缘 Agent 拉取租约并通过预签名 URL 与 S3
        直传，便于网关与扩展。
      </>
    ),
  },
  {
    title: '定时、策略与可观测性',
    Svg: require('@site/static/img/undraw_docusaurus_tree.svg').default,
    description: (
      <>
        策略与 Cron 调度、任务取消与重试、Prometheus 指标与简易 Web UI，覆盖从开发到小规模自托管的常见需求。
      </>
    ),
  },
  {
    title: 'Python 与容器友好',
    Svg: require('@site/static/img/undraw_docusaurus_react.svg').default,
    description: (
      <>
        提供 Docker Compose 与本地开发说明；文档站与代码同仓，便于随版本迭代更新。
      </>
    ),
  },
];

function Feature({title, Svg, description}: FeatureItem) {
  return (
    <div className={clsx('col col--4')}>
      <div className="text--center">
        <Svg className={styles.featureSvg} role="img" />
      </div>
      <div className="text--center padding-horiz--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
