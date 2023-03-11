from aws_cdk import (
    aws_ec2 as ec2,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
    aws_ecr as ecr,
    aws_s3 as s3,
    aws_codedeploy as codedeploy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    Duration, Stack
)
import aws_cdk as cdk
from constructs import Construct
import os
class FlaskPipelineStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a CodePipeline to build and deploy the Flask app
        pipeline = codepipeline.Pipeline(
            self, "FlaskPipeline",
            pipeline_name="flask-pipeline",
        )

        # Create a VPC
        vpc = ec2.Vpc(
            self, "FlaskVPC",
            cidr="10.0.0.0/16",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ]
        )

        # Create a key pair
        key_pair = ec2.CfnKeyPair(
            self, "MyKeyPair",
            key_name="my-key-pair"
        )

        # Create a security group
        security_group = ec2.SecurityGroup(
            self, "MySecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name="my-security-group"
        )

        # Allow SSH access to the EC2 instance
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "Allow SSH access"
        )

        # Allow access to port 5000
        security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(5000),
            "Allow access to port 5000"
        )

        # Launch an EC2 instance with the key pair
        instance = ec2.Instance(
            self, "MyInstance",
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            vpc=vpc,
            security_group=security_group,
            key_name=key_pair.key_name,
        )

        # Output the public DNS name of the instance
        cdk.CfnOutput(
            self, "InstancePublicDnsName",
            value=instance.instance_public_dns_name,
        )

        # Allow CodePipeline to access the EC2 instance
        # instance.grant_connect(instances=[instance])

        # Create a CodeCommit repository for the Flask app
        repository = codecommit.Repository(
            self, "FlaskRepository",
            repository_name="flask-repo",
            description="A repository for the Flask app",
            code=codecommit.Code.from_directory(os.getcwd(), "master")
        )

        # Output the CodeCommit repository URL
        cdk.CfnOutput(
            self, "FlaskRepositoryUrl",
            value=repository.repository_clone_url_http,
            description="Flask repository URL",
        )

        # Create an ECR repository to store the Docker image
        ecr_repository = ecr.Repository(
            self, "FlaskECRRepository",
            repository_name="flask-ecr-repo",
        )

        # Source stage: Retrieve code from CodeCommit repository
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="RetrieveSource",
            repository=repository,
            output=source_output,
            branch="master",
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action],
        )

        # Build stage: Build Docker image and push to ECR
        build_output = codepipeline.Artifact()
        build_action = codepipeline_actions.CodeBuildAction(
            action_name="BuildAndPushDockerImage",
            project=codebuild.PipelineProject(
                self, "FlaskCodeBuildProject",
                environment=codebuild.BuildEnvironment(
                    build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_3,
                    privileged=True,
                ),
                build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",
                    "phases": {
                        "build": {
                            "commands": [
                                "echo 'Starting build'",
                                f"docker build -t {ecr_repository.repository_uri}:latest .",
                                "$(aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URL)",
                                f"docker push {ecr_repository.repository_uri}:latest",
                            ]
                        }
                    },
                    "artifacts": {
                        "files": [
                            "Dockerfile",
                            "**/*",
                        ],
                        "base-directory": ".",
                        "discard-paths": "no",
                    },
                }),
            ),
            input=source_output,
            outputs=[build_output],
            environment_variables={
                "ECR_REPOSITORY_URL": codebuild.BuildEnvironmentVariable(
                    value=ecr_repository.repository_uri,
                    ),
                },
            )
        pipeline.add_stage(
            stage_name="Build",
            actions=[build_action],
        )

        # Deploy stage: Deploy the Flask app to EC2 using CodeDeploy
        # codedeploy_bucket = s3.Bucket(
        #     self, "CodeDeployBucket",
        #     bucket_name="codedeploy-bucket",
        #     versioned=True,
        #     removal_policy=cdk.RemovalPolicy.DESTROY,
        # )
        #
        # # Create a CodeDeploy deployment group
        # deployment_group = codedeploy.ServerDeploymentGroup(
        #     self, "DeploymentGroup",
        #     application=my_application,
        #     deployment_group_name="MyDeploymentGroup",
        #     auto_scaling_groups=[asg],
        #     deployment_config=codedeploy.ServerDeploymentConfig.ALL_AT_ONCE
        # )
        #
        # # Add the CodeDeploy deployment action to the pipeline
        # deploy_action = codepipeline_actions.CodeDeployServerDeployAction(
        #     action_name="DeployToEc2",
        #     deployment_group=deployment_group,
        #     input=source_output,
        #     run_order=3
        # )
        # pipeline.add_stage(
        #     stage_name="Deploy",
        #     actions=[deploy_action]
        # )

