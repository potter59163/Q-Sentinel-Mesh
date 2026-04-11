import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecsPatterns from "aws-cdk-lib/aws-ecs-patterns";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import * as cloudwatchActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subscriptions from "aws-cdk-lib/aws-sns-subscriptions";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import { Construct } from "constructs";

export class QSentinelStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const apiDomainName = this.node.tryGetContext("apiDomainName") as string | undefined;
    const hostedZoneName = this.node.tryGetContext("hostedZoneName") as string | undefined;
    const hostedZoneId = this.node.tryGetContext("hostedZoneId") as string | undefined;
    const alarmEmail = this.node.tryGetContext("alarmEmail") as string | undefined;
    const existingRuntimeBucketName = this.node.tryGetContext("existingRuntimeBucketName") as string | undefined;

    let hostedZone: route53.IHostedZone | undefined;
    if (hostedZoneName) {
      hostedZone = hostedZoneId
        ? route53.HostedZone.fromHostedZoneAttributes(this, "HostedZone", {
            hostedZoneId,
            zoneName: hostedZoneName,
          })
        : route53.HostedZone.fromLookup(this, "HostedZone", {
            domainName: hostedZoneName,
          });
    }

    const shouldUseHttpsDomain = Boolean(apiDomainName && hostedZone);
    const certificate = shouldUseHttpsDomain
      ? new acm.Certificate(this, "ApiCertificate", {
          domainName: apiDomainName!,
          validation: acm.CertificateValidation.fromDns(hostedZone!),
        })
      : undefined;

    const alertTopic = new sns.Topic(this, "AlertsTopic", {
      topicName: "q-sentinel-alerts",
      displayName: "Q-Sentinel Production Alerts",
    });
    if (alarmEmail) {
      alertTopic.addSubscription(new subscriptions.EmailSubscription(alarmEmail));
    }

    // ── S3 Bucket ─────────────────────────────────────────────────────
    const managedBucket = existingRuntimeBucketName
      ? undefined
      : new s3.Bucket(this, "DataBucket", {
          bucketName: `q-sentinel-app-${this.account}`,
          blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
          encryption: s3.BucketEncryption.S3_MANAGED,
          bucketKeyEnabled: true,
          enforceSSL: true,
          versioned: true,
          removalPolicy: cdk.RemovalPolicy.RETAIN,
          cors: [
            {
              allowedMethods: [s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
              allowedOrigins: ["*"],
              allowedHeaders: ["*"],
              maxAge: 3000,
            },
          ],
          lifecycleRules: [
            {
              id: "expire-ct-uploads-fast",
              prefix: "ct-uploads/",
              expiration: cdk.Duration.days(7),
            },
            {
              id: "retain-heatmaps-30d",
              prefix: "heatmaps/",
              expiration: cdk.Duration.days(30),
            },
            {
              id: "retain-reports-90d",
              prefix: "reports/",
              expiration: cdk.Duration.days(90),
            },
            {
              id: "retain-results-180d",
              prefix: "results/",
              expiration: cdk.Duration.days(180),
            },
          ],
        });

    const dataBucket: s3.IBucket = existingRuntimeBucketName
      ? s3.Bucket.fromBucketName(this, "ImportedRuntimeBucket", existingRuntimeBucketName)
      : managedBucket!;

    // ── Secrets Manager ───────────────────────────────────────────────
    const appSecret = new secretsmanager.Secret(this, "AppSecret", {
      secretName: "q-sentinel/app",
      description: "Q-Sentinel Mesh application secrets",
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          CORS_ORIGINS: '["*"]',
          AWS_DEFAULT_REGION: "ap-southeast-7",
          DB_URL: "",
          THIRD_PARTY_API_KEY: "",
        }),
        generateStringKey: "JWT_SECRET",
        excludePunctuation: false,
        passwordLength: 64,
        includeSpace: false,
      },
    });

    // ── ECR Repository ────────────────────────────────────────────────
    const ecrRepo = new ecr.Repository(this, "BackendRepo", {
      repositoryName: "q-sentinel-backend",
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      imageScanOnPush: true,
      lifecycleRules: [
        {
          maxImageCount: 5,
          description: "Keep last 5 images",
        },
      ],
    });

    // ── VPC ───────────────────────────────────────────────────────────
    const vpc = new ec2.Vpc(this, "VPC", {
      vpcName: "q-sentinel-vpc",
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: "public",
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: "private",
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
      ],
    });

    // ── ECS Cluster ───────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc,
      clusterName: "q-sentinel-cluster",
      containerInsights: true,
    });

    // ── Task Execution Role ───────────────────────────────────────────
    const executionRole = new iam.Role(this, "ExecutionRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AmazonECSTaskExecutionRolePolicy"
        ),
      ],
    });

    // ── Task Role (S3 + Secrets access) ───────────────────────────────
    const taskRole = new iam.Role(this, "TaskRole", {
      assumedBy: new iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
    });
    dataBucket.grantReadWrite(taskRole);
    appSecret.grantRead(taskRole);
    appSecret.grantRead(executionRole);

    // ── Log Group ─────────────────────────────────────────────────────
    const logGroup = new logs.LogGroup(this, "BackendLogs", {
      logGroupName: "/ecs/q-sentinel-backend",
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── Task Definition ───────────────────────────────────────────────
    const taskDef = new ecs.FargateTaskDefinition(this, "TaskDef", {
      cpu: 1024,
      memoryLimitMiB: 4096,
      executionRole,
      taskRole,
    });

    // Use placeholder on bootstrap run; real image once CI/CD pushes it
    const bootstrapMode = this.node.tryGetContext("bootstrap") === "true";
    const containerImage = bootstrapMode
      ? ecs.ContainerImage.fromRegistry("public.ecr.aws/docker/library/python:3.11-slim")
      : ecs.ContainerImage.fromEcrRepository(ecrRepo, "latest");

    taskDef.addContainer("backend", {
      image: containerImage,
      command: bootstrapMode
        ? ["python3", "-c", "import http.server,socketserver; H=type('H',( http.server.BaseHTTPRequestHandler,),{'do_GET':lambda s:(s.send_response(200),s.end_headers(),s.wfile.write(b'OK'))}); socketserver.TCPServer(('',8000),H).serve_forever()"]
        : undefined,
      portMappings: [{ containerPort: 8000 }],
      environment: {
        AWS_REGION: this.region,
        S3_BUCKET: dataBucket.bucketName,
        PYTHONUNBUFFERED: "1",
        USE_S3: "true",
        WEIGHTS_S3_PREFIX: "weights/",
        RESULTS_S3_PREFIX: "results/",
        CT_UPLOAD_S3_PREFIX: "ct-uploads/",
      },
      secrets: {
        JWT_SECRET: ecs.Secret.fromSecretsManager(appSecret, "JWT_SECRET"),
        CORS_ORIGINS: ecs.Secret.fromSecretsManager(appSecret, "CORS_ORIGINS"),
        DB_URL: ecs.Secret.fromSecretsManager(appSecret, "DB_URL"),
        THIRD_PARTY_API_KEY: ecs.Secret.fromSecretsManager(appSecret, "THIRD_PARTY_API_KEY"),
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "backend",
        logGroup,
      }),
      healthCheck: {
        command: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')\" || exit 1"],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10),
        retries: 3,
        startPeriod: cdk.Duration.seconds(120),
      },
    });

    // ── Fargate Service + ALB ─────────────────────────────────────────
    const fargateService = new ecsPatterns.ApplicationLoadBalancedFargateService(
      this,
      "BackendService",
      {
        cluster,
        taskDefinition: taskDef,
        desiredCount: bootstrapMode ? 1 : 1,
        publicLoadBalancer: true,
        listenerPort: shouldUseHttpsDomain ? 443 : 80,
        redirectHTTP: shouldUseHttpsDomain,
        domainName: shouldUseHttpsDomain ? apiDomainName : undefined,
        domainZone: shouldUseHttpsDomain ? hostedZone : undefined,
        certificate,
        healthCheckGracePeriod: cdk.Duration.seconds(180),
        loadBalancerName: "q-sentinel-alb",
        serviceName: "q-sentinel-backend",
        assignPublicIp: false,
      }
    );

    // Disable ECS circuit-breaker rollback so CloudFormation doesn't time out
    const cfnSvc = fargateService.service.node.defaultChild as ecs.CfnService;
    cfnSvc.deploymentConfiguration = {
      deploymentCircuitBreaker: { enable: true, rollback: false },
      maximumPercent: 200,
      minimumHealthyPercent: 50,
    };

    fargateService.targetGroup.configureHealthCheck({
      path: "/api/health",
      healthyHttpCodes: "200",
      interval: cdk.Duration.seconds(30),
      timeout: cdk.Duration.seconds(10),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 5,
    });

    const scalableTarget = fargateService.service.autoScaleTaskCount({
      minCapacity: 1,
      maxCapacity: 4,
    });
    scalableTarget.scaleOnCpuUtilization("CpuScaling", {
      targetUtilizationPercent: 60,
      scaleInCooldown: cdk.Duration.seconds(120),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });
    scalableTarget.scaleOnMemoryUtilization("MemoryScaling", {
      targetUtilizationPercent: 70,
      scaleInCooldown: cdk.Duration.seconds(120),
      scaleOutCooldown: cdk.Duration.seconds(60),
    });

    const target5xxAlarm = new cloudwatch.Alarm(this, "AlbTarget5xxAlarm", {
      alarmName: "q-sentinel-alb-target-5xx",
      metric: fargateService.targetGroup.metricHttpCodeTarget(
        elbv2.HttpCodeTarget.TARGET_5XX_COUNT,
        {
          period: cdk.Duration.minutes(1),
          statistic: "sum",
        }
      ),
      threshold: 5,
      evaluationPeriods: 2,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    const latencyAlarm = new cloudwatch.Alarm(this, "AlbLatencyAlarm", {
      alarmName: "q-sentinel-alb-latency-p95",
      metric: fargateService.loadBalancer.metricTargetResponseTime({
        period: cdk.Duration.minutes(1),
        statistic: "p95",
      }),
      threshold: 2,
      evaluationPeriods: 3,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    const cpuAlarm = new cloudwatch.Alarm(this, "EcsCpuHighAlarm", {
      alarmName: "q-sentinel-ecs-cpu-high",
      metric: fargateService.service.metricCpuUtilization({
        period: cdk.Duration.minutes(1),
        statistic: "Average",
      }),
      threshold: 80,
      evaluationPeriods: 3,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    const memoryAlarm = new cloudwatch.Alarm(this, "EcsMemoryHighAlarm", {
      alarmName: "q-sentinel-ecs-memory-high",
      metric: fargateService.service.metricMemoryUtilization({
        period: cdk.Duration.minutes(1),
        statistic: "Average",
      }),
      threshold: 85,
      evaluationPeriods: 3,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    const unhealthyTargetsAlarm = new cloudwatch.Alarm(this, "AlbUnhealthyTargetsAlarm", {
      alarmName: "q-sentinel-alb-unhealthy-targets",
      metric: fargateService.targetGroup.metricUnhealthyHostCount({
        period: cdk.Duration.minutes(1),
        statistic: "Maximum",
      }),
      threshold: 1,
      evaluationPeriods: 2,
      datapointsToAlarm: 2,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });

    target5xxAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    latencyAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    cpuAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    memoryAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    unhealthyTargetsAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

    // GitHub Actions role (OIDC) for CI/CD
    const githubOidcProvider = new iam.OpenIdConnectProvider(
      this,
      "GithubOidcProvider",
      {
        url: "https://token.actions.githubusercontent.com",
        clientIds: ["sts.amazonaws.com"],
        thumbprints: ["6938fd4d98bab03faadb97b34396831e3780aea1"],
      }
    );

    const ciRole = new iam.Role(this, "GithubActionsRole", {
      roleName: "q-sentinel-github-actions",
      assumedBy: new iam.WebIdentityPrincipal(
        githubOidcProvider.openIdConnectProviderArn,
        {
          StringEquals: {
            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          },
          StringLike: {
            "token.actions.githubusercontent.com:sub":
              "repo:potter59163/Q-Sentinel-Mesh:*",
          },
        }
      ),
    });

    ecrRepo.grantPullPush(ciRole);
    ciRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:DescribeClusters",
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
        ],
        resources: [
          fargateService.service.serviceArn,
          cluster.clusterArn,
          "*",
        ],
      })
    );
    ciRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        resources: [executionRole.roleArn, taskRole.roleArn],
      })
    );
    dataBucket.grantReadWrite(ciRole);
    alertTopic.grantPublish(ciRole);

    // ── Frontend ECR ──────────────────────────────────────────────────
    const frontendEcrRepo = new ecr.Repository(this, "FrontendEcr", {
      repositoryName: "q-sentinel-frontend",
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [{ maxImageCount: 5, description: "Keep last 5 images" }],
    });
    frontendEcrRepo.grantPullPush(executionRole);
    frontendEcrRepo.grantPullPush(ciRole);

    // ── Frontend Task Definition ──────────────────────────────────────
    const frontendTaskDef = new ecs.FargateTaskDefinition(this, "FrontendTaskDef", {
      cpu: 512,
      memoryLimitMiB: 1024,
      executionRole,
      taskRole,
    });

    const frontendLogGroup = new logs.LogGroup(this, "FrontendLogs", {
      logGroupName: "/ecs/q-sentinel-frontend",
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const apiUrl = shouldUseHttpsDomain
      ? `https://${apiDomainName}`
      : `http://${fargateService.loadBalancer.loadBalancerDnsName}`;

    const frontendImage = bootstrapMode
      ? ecs.ContainerImage.fromRegistry("public.ecr.aws/docker/library/node:20-alpine")
      : ecs.ContainerImage.fromEcrRepository(frontendEcrRepo, "latest");

    frontendTaskDef.addContainer("frontend", {
      image: frontendImage,
      command: bootstrapMode
        ? ["node", "-e", "require('http').createServer((_,r)=>{r.writeHead(200);r.end('Q-Sentinel Frontend')}).listen(3000)"]
        : undefined,
      portMappings: [{ containerPort: 3000 }],
      environment: {
        NODE_ENV: "production",
        NEXT_PUBLIC_API_URL: apiUrl,
        PORT: "3000",
        HOSTNAME: "0.0.0.0",
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "frontend",
        logGroup: frontendLogGroup,
      }),
      healthCheck: {
        command: ["CMD-SHELL", "node -e \"require('http').get('http://localhost:3000', r => process.exit(r.statusCode < 500 ? 0 : 1))\" || exit 1"],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(10),
        retries: 3,
        startPeriod: cdk.Duration.seconds(120),
      },
    });

    // ── Frontend Fargate Service + ALB ────────────────────────────────
    const frontendService = new ecsPatterns.ApplicationLoadBalancedFargateService(
      this,
      "FrontendService",
      {
        cluster,
        taskDefinition: frontendTaskDef,
        desiredCount: 1,
        publicLoadBalancer: true,
        listenerPort: 80,
        targetProtocol: elbv2.ApplicationProtocol.HTTP,
        healthCheckGracePeriod: cdk.Duration.seconds(180),
        loadBalancerName: "q-sentinel-frontend-alb",
        serviceName: "q-sentinel-frontend",
        circuitBreaker: { enable: true, rollback: false },
      }
    );

    frontendService.targetGroup.configureHealthCheck({
      path: "/",
      healthyHttpCodes: "200-399",
      interval: cdk.Duration.seconds(30),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 5,
    });

    // Allow CI to update frontend service
    ciRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ecs:UpdateService", "ecs:DescribeServices"],
        resources: [frontendService.service.serviceArn],
      })
    );

    // ── CloudFront Distribution ───────────────────────────────────────
    const distribution = new cloudfront.Distribution(this, "FrontendCdn", {
      defaultBehavior: {
        origin: new origins.HttpOrigin(frontendService.loadBalancer.loadBalancerDnsName, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
      },
      additionalBehaviors: {
        // Static assets — aggressive caching
        "_next/static/*": {
          origin: new origins.HttpOrigin(frontendService.loadBalancer.loadBalancerDnsName, {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        },
        // Backend API — proxy through CloudFront so frontend HTTPS → HTTPS
        "api/*": {
          origin: new origins.HttpOrigin(fargateService.loadBalancer.loadBalancerDnsName, {
            protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          }),
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.HTTPS_ONLY,
          cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
          allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
          originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        },
      },
      comment: "Q-Sentinel Frontend CDN",
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
    });

    // ── Outputs ───────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "ApiUrl", {
      value: shouldUseHttpsDomain
        ? `https://${apiDomainName}`
        : `http://${fargateService.loadBalancer.loadBalancerDnsName}`,
      exportName: "QSentinelApiUrl",
      description: "Backend API URL",
    });

    new cdk.CfnOutput(this, "BucketName", {
      value: dataBucket.bucketName,
      exportName: "QSentinelBucketName",
      description: "S3 bucket for weights, results, CT uploads",
    });

    new cdk.CfnOutput(this, "EcrUri", {
      value: ecrRepo.repositoryUri,
      exportName: "QSentinelEcrUri",
      description: "ECR URI — used by GitHub Actions",
    });

    new cdk.CfnOutput(this, "ClusterName", {
      value: cluster.clusterName,
      exportName: "QSentinelClusterName",
    });

    new cdk.CfnOutput(this, "ServiceName", {
      value: fargateService.service.serviceName,
      exportName: "QSentinelServiceName",
    });

    new cdk.CfnOutput(this, "GithubActionsRoleArn", {
      value: ciRole.roleArn,
      exportName: "QSentinelGithubActionsRoleArn",
      description: "IAM Role ARN — add as AWS_ROLE_ARN secret in GitHub",
    });

    new cdk.CfnOutput(this, "AlbDnsName", {
      value: fargateService.loadBalancer.loadBalancerDnsName,
      exportName: "QSentinelAlbDnsName",
      description: "ALB DNS name",
    });

    if (shouldUseHttpsDomain) {
      new cdk.CfnOutput(this, "ApiDomainName", {
        value: apiDomainName!,
        exportName: "QSentinelApiDomainName",
        description: "Route53 + ACM-backed API domain",
      });
    }

    new cdk.CfnOutput(this, "AlertsTopicArn", {
      value: alertTopic.topicArn,
      exportName: "QSentinelAlertsTopicArn",
      description: "SNS topic for CloudWatch alarms",
    });

    new cdk.CfnOutput(this, "FrontendEcrUri", {
      value: frontendEcrRepo.repositoryUri,
      exportName: "QSentinelFrontendEcrUri",
      description: "Frontend ECR URI — used by GitHub Actions",
    });

    new cdk.CfnOutput(this, "FrontendServiceName", {
      value: frontendService.service.serviceName,
      exportName: "QSentinelFrontendServiceName",
    });

    new cdk.CfnOutput(this, "FrontendAlbDnsName", {
      value: frontendService.loadBalancer.loadBalancerDnsName,
      exportName: "QSentinelFrontendAlbDnsName",
    });

    new cdk.CfnOutput(this, "FrontendUrl", {
      value: `https://${distribution.distributionDomainName}`,
      exportName: "QSentinelFrontendUrl",
      description: "CloudFront URL for the frontend",
    });
  }
}
