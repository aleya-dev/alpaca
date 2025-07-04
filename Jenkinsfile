pipeline {
    agent { label 'local' }

    environment {
        PYPI_USERNAME = '__token__'
        PYPI_PASSWORD = credentials('pypy_token')
    }

    stages {
        stage('Install Build Dependencies') {
            steps {
                sh '''
                    python3 -m pip install --upgrade pip
                    python3 -m pip install build pytest twine requests
                '''
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
                    return sh(script: "git tag --points-at HEAD", returnStatus: true) == 0
                }
            }
            steps {
                script {
                    def tag = sh(script: "git tag --points-at HEAD", returnStdout: true).trim()
                    def version = tag.replaceFirst(/^v/, '')

                    def pkgName = "aleya-alpaca"

                    def exists = sh(
                        script: "python3 -c \"import requests; r = requests.get(f'https://pypi.org/pypi/${pkgName}/${version}/json'); exit(0) if r.status_code == 200 else exit(1)\"",
                        returnStatus: true
                    )

                    if (exists == 0) {
                        echo "Version ${version} of ${pkgName} already exists on PyPI. Skipping upload."
                    } else {
                        sh '''
                            python3 -m twine upload \
                                --username "$PYPI_USERNAME" \
                                --password "$PYPI_PASSWORD" \
                                dist/*
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'dist/*', fingerprint: true
        }
    }
}
