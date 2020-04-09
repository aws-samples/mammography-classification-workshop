#!/bin/bash

cloudfront_stack_name='mammography-workshop-cloudfront'
front_stack_name='mammography-workshop-client-front'
back_stack_name='mammography-workshop-client-back'
set_up_stack_name='mammography-workshop-set-up'
#set_up_stack_name is defined in the README.md root file, in 1 - Creating the SageMaker Jupyter Notebook

usage() {
    echo "usage: $0 <command>"

    echo "Available commands:"
    echo -e "  create \tCreate client resources"
    echo -e "  delete\tDelete client resources"
}

create() {

  # Mandatory parameter validation
  validate_mandatory_parameters

  # Frontend resources
  echo "Deploying Client App frontend..."
  echo "Creating CloudFormation stack. This can take about 3 minutes..."
	stack_id_front=$(aws cloudformation create-stack --stack-name $front_stack_name --template-body file://frontend_client_template.yml --capabilities CAPABILITY_NAMED_IAM --output text --query StackId)

	stack_status_check="aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].StackStatus"
	stack_status=$($stack_status_check)

	while [ $stack_status != "CREATE_COMPLETE" ]; do
		echo "Checking CloudFormation stack status..."
		if [[ $stack_status == ROLLBACK_* ]]; then
			echo "Something went wrong. Please check CloudFormation events in the AWS Console"
			exit 1
		fi
		sleep 3
		stack_status=$($stack_status_check)
	done
	echo "Stack created successfully!"


  cognito_id=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`CognitoIdentityPoolId\`].OutputValue)
  region=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`Region\`].OutputValue)
  website_bucket=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`S3StaticWebsiteBucket\`].OutputValue)
  private_bucket=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`PrivateBucket\`].OutputValue)
  origin_access_identity=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`CloudFrontOriginAccessIdentity\`].OutputValue)
  origin_domain_name=$(aws cloudformation describe-stacks --stack-name $stack_id_front --output text --query Stacks[0].Outputs[?OutputKey==\`OriginDomainName\`].OutputValue)

	echo "Deploying CloudFront ..."

  stack_id_cloudfront=$(aws cloudformation create-stack --stack-name $cloudfront_stack_name --template-body file://cloudfront_template.yml --parameters ParameterKey=CloudFrontOriginAccessIdentity,ParameterValue=$origin_access_identity ParameterKey=S3StaticWebsiteBucket,ParameterValue=$origin_domain_name --capabilities CAPABILITY_NAMED_IAM --output text --query StackId)
  # Since this will take several minutes to deploy, we won't keep track of its status. Let's move on.

	echo "Uploading frontend..."
  cat > ../client-app/frontend/config.js << EOL

  const REGION='$region'
  const COGNITO_ID='$cognito_id'
  const PRIVATE_BUCKET='$private_bucket'
EOL

	aws s3 cp ../client-app/frontend/ s3://$website_bucket --recursive --quiet

  # Backend resources
  echo "Deploying Client App backend..."
  echo "Creating CloudFormation stack. This can take about 3 minutes..."
  zip -j ../client-app/lambda/code/lambda_invoke_classifier.zip ../client-app/lambda/code/lambda_invoke_classifier.py --quiet
  zip -j ../client-app/lambda/code/lambda_resize_image.zip ../client-app/lambda/code/lambda_resize_image.py --quiet
  aws s3 cp ../client-app/lambda/ s3://$private_bucket --recursive --quiet

  set_up_bucket=$(aws cloudformation describe-stacks --stack-name $set_up_stack_name --output text --query Stacks[0].Outputs[?OutputKey==\`MammographyBucket\`].OutputValue)


  stack_id_back=$(aws cloudformation create-stack --stack-name $back_stack_name --template-body file://backend_client_template.yml --parameters ParameterKey=Endpoint,ParameterValue=$endpoint ParameterKey=PrivateBucket,ParameterValue=$private_bucket ParameterKey=SetUpBucket,ParameterValue=$set_up_bucket  --capabilities CAPABILITY_NAMED_IAM --output text --query StackId)
  stack_status_check="aws cloudformation describe-stacks --stack-name $stack_id_back --output text --query Stacks[0].StackStatus"
	stack_status=$($stack_status_check)
  while [ $stack_status != "CREATE_COMPLETE" ]; do
		echo "Checking CloudFormation stack status..."
		if [[ $stack_status == ROLLBACK_* ]]; then
			echo "Something went wrong. Please check CloudFormation events in the AWS Console"
			exit 1
		fi
		sleep 3
		stack_status=$($stack_status_check)
	done
	echo "Stack created successfully!"

  # Outputs

  outputs

}
validate_mandatory_parameters(){

  # Mandatory parameter validation
  endpoint=$(aws sagemaker list-endpoints --sort-by 'CreationTime' --sort-order 'Descending' --status-equals 'InService' --name-contains 'mammography-classification-' --query Endpoints[0].EndpointName)
  if [ $endpoint == 'null' ]; then
      endpoint_not_ready=$(aws sagemaker list-endpoints --sort-by 'CreationTime' --sort-order 'Descending' --status-equals 'Creating' --name-contains 'mammography-classification-' --query Endpoints[0].EndpointName)

      if [ $endpoint_not_ready != 'null' ]; then
  			echo "Your endpoint is not In Service yet. Wait a few minutes and try again."
  			exit 1

      fi

			echo "Your model endpoint could not be found. Access https://console.aws.amazon.com/sagemaker/home?#/endpoints/ to make sure you have an endpoint called 'mammography-classification-<timestamp>' deployed."
			exit 1

  fi

}

outputs(){

#  yum install jq -> not necessary when in AWS Jupyter Notebook

  distribution=$(aws cloudfront list-distributions --query DistributionList.Items[*])
  printf "%s" "$distribution" > "distribution.json"

  echo "."
  echo "Copy below the URL for your website:"

  jq -r ' .[] | select( .Origins.Items[].DomainName | startswith("mammography-static-website")) | .DomainName' distribution.json
}

delete() {
    echo "Deleting all the resources created for this workshop..."


    website_bucket=$(aws cloudformation describe-stacks --stack-name $front_stack_name --output text --query Stacks[0].Outputs[?OutputKey==\`S3StaticWebsiteBucket\`].OutputValue)
    private_bucket=$(aws cloudformation describe-stacks --stack-name $front_stack_name --output text --query Stacks[0].Outputs[?OutputKey==\`PrivateBucket\`].OutputValue)
    set_up_bucket=$(aws cloudformation describe-stacks --stack-name $set_up_stack_name --output text --query Stacks[0].Outputs[?OutputKey==\`MammographyBucket\`].OutputValue)

    aws s3 rm s3://$website_bucket/ --recursive --quiet
    aws s3 rm s3://$private_bucket/ --recursive --quiet
    aws s3 rm s3://$set_up_bucket/ --recursive --quiet

    aws cloudformation delete-stack --stack-name $back_stack_name
    aws cloudformation wait stack-delete-complete --stack-name $back_stack_name
    echo 'Backend stack deleted.'

    aws cloudformation delete-stack --stack-name $cloudfront_stack_name
    aws cloudformation wait stack-delete-complete --stack-name $cloudfront_stack_name
    echo 'CloudFront stack deleted.'

    # Cloudfront stack has dependencies with the front stack. Only delete this one after deleting CloudFront stack.
    aws cloudformation delete-stack --stack-name $front_stack_name
    aws cloudformation wait stack-delete-complete --stack-name $front_stack_name
    echo 'Front stack deleted.'


    echo 'Deleting the SageMaker endpoint, and the mammography-workshop-set-up cloudformation stack...'
    echo 'Attention: this will delete this notebook. Prepare for shut down.'
    # Deleting the sagemaker_template.yml ($set_up_stack_name)
    # This will even delete this notebook
    endpoint=$(aws sagemaker list-endpoints --sort-by 'CreationTime' --sort-order 'Descending' --status-equals 'InService' --name-contains 'mammography-classification-' --query Endpoints[0].EndpointName)

    if [ $endpoint != 'null' ]; then
      aws sagemaker delete-endpoint --endpoint-name $endpoint
    fi


    aws cloudformation delete-stack --stack-name $set_up_stack_name
    echo 'Shutting down.'

}

if [[ $# -gt 0 ]]; then
    command=$1

    case $command in

    create )
          create
        ;;

    delete )
        delete
        ;;

    * )
        usage
        exit 1

    esac
else
    usage
    exit
fi