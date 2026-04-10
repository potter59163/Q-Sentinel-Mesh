import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as ecsPatterns from "aws-cdk-lib/aws-ecs-patterns";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import { Construct } from "constructs";

export class QSentinelStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ── S3 Bucket ─────────────────────────────────────────────────────
    const dataBucket = new s3.Bucket(this, "DataBucket", {
      bucketName: `q-sentinel-data-${this.account}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      versioned: false,
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
          id: "expire-ct-uploads",
          prefix: "ct-uploads/",
          expiration: cdk.Duration.days(7),
        },
      ],
    });

    // ── Secrets Manager ───────────────────────────────────────────────
    const appSecret = new secretsmanager.Secret(this, "AppSecret", {
      secretName: "q-sentinel/app",
      description: "Q-Sentinel Mesh application secrets",
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          DEMO_PASSWORD: "qsentinel2026",
          CORS_ORIGINS: '["*"]',
          AWS_DEFAULT_REGION: "ap-southeast-7",
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
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── Task Definition ───────────────────────────────────────────────
    const taskDef = new ecs.FargateTaskDefinition(this, "TaskDef", {
      cpu: 2048,
      memoryLimitMiB: 8192,
      executionRole,
      taskRole,
    });

    taskDef.addContainer("backend", {
      image: ecs.ContainerImage.fromEcrRepository(ecrRepo, "latest"),
      portMappings: [{ containerPort: 8000 }],
      environment: {
        AWS_REGION: this.region,
        S3_BUCKET: dataBucket.bucketName,
        PYTHONUNBUFFERED: "1",
      },
      secrets: {
        JWT_SECRET: ecs.Secret.fromSecretsManager(appSecret, "JWT_SECRET"),
        DEMO_PASSWORD: ecs.Secret.fromSecretsManager(appSecret, "DEMO_PASSWORD"),
        CORS_ORIGINS: ecs.Secret.fromSecretsManager(appSecret, "CORS_ORIGINS"),
      },
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: "backend",
        logGroup,
      }),
      healthCheck: {
        command: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"],
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
        desiredCount: 1,
        publicLoadBalancer: true,
        listenerPort: 80,
        healthCheckGracePeriod: cdk.Duration.seconds(180),
        loadBalancerName: "q-sentinel-alb",
        serviceName: "q-sentinel-backend",
        assignPublicIp: false,
      }
    );

    fargateService.targetGroup.configureHealthCheck({
      path: "/api/health",
      healthyHttpCodes: "200",
      interval: cdk.Duration.seconds(30),
      timeout: cdk.Duration.seconds(10),
      healthyThresholdCount: 2,
      unhealthyThresholdCount: 5,
    });

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
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
        ],
        resources: ["*"],
      })
    );
    ciRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["iam:PassRole"],
        resources: [executionRole.roleArn, taskRole.roleArn],
      })
    );
    dataBucket.grantReadWrite(ciRole);

    // ── Amplify Service Role ──────────────────────────────────────────
    const amplifyRole = new iam.Role(this, "AmplifyRole", {
      roleName: "q-sentinel-amplify-role",
      assumedBy: new iam.ServicePrincipal("amplify.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AdministratorAccess-Amplify"),
      ],
    });

    // ── Outputs ───────────────────────────────────────────────────────
    new cdk.CfnOutput(this, "ApiUrl", {
      value: `http://${fargateService.loadBalancer.loadBalancerDnsName}`,
      exportName: "QSentinelApiUrl",
      description: "Backend API URL — set as NEXT_PUBLIC_API_URL in Amplify",
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

    new cdk.CfnOutput(this, "AmplifyRoleArn", {
      value: amplifyRole.roleArn,
      exportName: "QSentinelAmplifyRoleArn",
      description: "Amplify service role ARN",
    });
  }
}
