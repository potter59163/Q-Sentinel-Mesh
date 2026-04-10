#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { QSentinelStack } from "../lib/q-sentinel-stack";

const app = new cdk.App();

new QSentinelStack(app, "QSentinelStack", {
  env: {
    account: "335158494927",
    region: "ap-southeast-7",
  },
  description: "Q-Sentinel Mesh — CEDT Hackathon 2026",
});
