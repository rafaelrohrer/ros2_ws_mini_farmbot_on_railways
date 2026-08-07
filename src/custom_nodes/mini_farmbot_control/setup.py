from setuptools import find_packages, setup

package_name = 'mini_farmbot_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            'share/' + package_name + '/launch',
            [
                'launch/send_test_trajectory.launch.py',
            ],
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rafaelrohrer',
    maintainer_email='rohreraf@students.zhaw.ch',
    description='Test client for sending trajectories to the mini farmbot controller.',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'send_test_trajectory = mini_farmbot_control.send_joint_trajectory:main',
            'fake_joint_trajectory_controller = mini_farmbot_control.fake_joint_trajectory_controller:main',
        ],
    },
)
