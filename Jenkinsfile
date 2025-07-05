pipeline {
    agent { label 'local' }

    parameters {
        string(name: 'REF', defaultValue: 'master', description: 'Git tag or branch to build')
        booleanParam(name: 'PUBLISH', defaultValue: false, description: 'Publish to PyPI')
    }

    environment {
        PYPI_USERNAME = '__token__'
        PYPI_PASSWORD = credentials('pypy_token')
    }

    stages {
        stage('Checkout') {
            steps {
                script {
                    def ref = params.REF?.trim()
                    sh "git checkout ${ref}"
                }
            }
        }

        stage('Run Tests') {
            steps {
                sh 'python3 -m pytest'
            }
        }

        stage('Build Package') {
            steps {
                sh 'python3 -m build'
            }
        }

        stage('Publish to PyPI') {
            when {
                expression {
                    params.PUBLISH
                }
            }
            steps {
                sh '''
                    python3 -m twine upload \
                        --username "$PYPI_USERNAME" \
                        --password "$PYPI_PASSWORD" \
                        dist/*
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'dist/*', fingerprint: true
        }
    }
}
