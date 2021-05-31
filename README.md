

# CA (Code Analyzer)
***

## Purpose

> With this CA, code can be inspected with the predefined rules regarding design rules.
When it comes to 'Rule of Five', the CA detects which class violates the rule and report the result.

&nbsp;

## Prerequisite

pip3 install pyfiglet termcolor
just do pip3 install -r requirements.txt

&nbsp;

## Features

### 1. design verification

* rules of five
  * checking whether the following methods are defined or not
    * destructor
    * copy constructor, copy assignment operator
    * move constructor, move assignment operator
* prohibit keywords
  * in interface classes, the following keywords are not allowed to use
    * protected
    * friends
    * pair
    * tuple
* nested class
  * nested class in the public access modifier are not permitted to use
* modularity (modular indices)
  * modularity is not 'must' to follow. It's 'should'
    * number of public methods are limited to 30 or less
    * number of parameters are limited to 7 or less
* component dependency analysis
* call dependency analysis
* and
  * other features can be added easily

&nbsp;

#### Usage

the CA can be executed as follow.

1. design verification
python main.py --cmd=verify --path=./

* argument types
  * cmd
    * operation to start
  * path
    * location to check
  * cover
    * 'all': print all the violations including not also 'must' items but 'should' items
    * 'must': print only 'must' items. it's default coverage

#### result
It shows result of analysis as table below.
user can easily find which module is the best one at the last colume of the table.

```
MISS 1941:
directory = /.../wayland/include
        file = /.../wayland/include/wayland.h:
                class = WaylandProtocol / ClassType.SINGLETON : missing num = 1
                misisng rules =  ['violate_modularity -> num public methods 44']
...
+---------------------------------------------------------------------------------------------------------------------+
| directory                 | files        | vio. files   | classes      | vio. classes | vio. count   | rank         |
+---------------------------------------------------------------------------------------------------------------------+
| ..it_control/core/include | 12           | 0            | 1            | 0            | 0            | .            |
| ..control/device_/include | 4            | 3            | 2            | 3            | 8            | 52           |
...
```

&nbsp;


#### report on web page

you can see the result with the web browser as follow by enabling "json_output" in the configuration file (cfg_ca.conf)

&nbsp;

```python
{
    ...
    "json_output": true
}
```

&nbsp;

### 2. comment verification
* verify whether comment is well commented or not 

&nbsp;

#### usage
python main.py --cmd=verify_comment --path=./ [--recursive_depth=2]


&nbsp;

#### result
test.h
```C++
class ITestListener {
public:
    /**
     * @brief The user might implement the constructor.
     */
    ITestListener() = default;

    /**
     * @brief The user might implement the destructor.
     */
    virtual ~ITestListener() = default;
};


class TestClass {
public:
    /**
     * @brief ...
     */
    void func1();

    ReturnType loop();

    void setEventListener(std::weak_ptr<ITestListener> listener);

    /**
     * @brief This function is to set check state
     * @param[in] AState
     */
    void setAState(const TestClassState& state);
};


class TestParamType {
public:
    /**
     * @brief This function is to get the current state of event feed
     * @retval BoolType event feed enable state
     */
    BoolType getEventFeed() const;

    /**
     * @brief copy constructor
     */
    TestParamType(const TestParamType& rhs);

    /**
     * @brief move constructor
     * @param[in] rhs: right-hand side reference
     */
    TestParamType(TestParamType&& rhs);

    /**
     * @brief parameterized constructor
     * @param[in] dev: Test device type
     * @param[in] notifcation: enable/disable event notification
     */
    explicit TestParamType(const TestDeviceType& dev,
            const BoolType& notification = true);

    /**
     * @brief copy assignment operator
     * @param[in] rhs to an instance of TestParamType
     * @retval reference to an instance of TestParamType
     * @since 0.17rc
     */
    const TestParamType& operator=(const TestParamType& rhs);

    /**
     * @brief move assignment operator
     * @param[in] rhs to an instance of TestParamType
     * @retval reference to an instance of TestParamType
     */
    const TestParamType& operator=(TestParamType&& rhs);
};
```
&nbsp;

result
```
 * stats: .../project_path/test : err=5
+------------------------------------------------------------------------------+
| file name                           | class name                     | # err |
+------------------------------------------------------------------------------+
| test.h                              | ITestListener                  | 0     |
+-------------------------------------+--------------------------------+-------+
| test.h                              | TestClass                      | 5     |
+-------------------------------------+--------------------------------+-------+
| test.h                              | TestParamType                  | 2     |
+-------------------------------------+--------------------------------+-------+

file: D:\projects\se\ca\test\test.h
        class:  TestClass
                >> method: loop is not documented @ 22
                >> method: setEventListener is not documented @ 24
                >> method: void setAState(const TestClassState& state) @ 29
                        >> 'state' is not documented @ 30
                        >> 'AState' does not exist in the code @ 30
        class:  TestParamType
                >> method: TestParamType(const TestParamType& rhs) @ 44
                        >> 'rhs' is not documented @ 45
                >> method: explicit TestParamType(const TestDeviceType& dev,
            const BoolType& notification = true) @ 57
                        >> 'notification' is not documented @ 58
                        >> 'notifcation' does not exist in the code @ 58
```

&nbsp;

### 3. S/W component dependency analysis
* it analyze all the dependencies of each S/W component in the given path
* and then 
  * 1) create dependency graph of components
  * 2) show stability of each component node by calculating fan-in and fan-out

#### usage
python main.py --cmd=dependency --path=project_path

&nbsp;

#### result
&nbsp;

### 4. call frequency analysis
call_dependency
&nbsp;

#### usage

##### 1. regular use
* main.py --cmd=call_dependency --ppath=api_path --upath=app_path

##### 2. save API analysis
* main.py --cmd=call_dependency --ppath=api_path --savefile=file_name

##### 3. use stored API analysis
* main.py --cmd=call_dependency --upath=app_path --loadfile=file_name

&nbsp;

#### result
&nbsp;

### 5. enumerate all the interfaces

#### usage
&nbsp;

#### result

```
/mnt/.../DataManager/include/DataFlowController.h
 +-  DataFlowController
 |     +- public method : // 27
 |     |     +-  static DataFlowController& getInstance()
 |     |     |     -> static DataFlowController&
 |     |     +-  HResult createDataPatch(const DataPatch& patch, HUInt64& handle)
 |     |     |     -> Result
 |     |     |     +-  params :  : // 2
 |     |     |     |      +-  const DataPatch& patch
 |     |     |     |      +-  HUInt64& handle
 |     |     +-  HResult releaseDataPatch(const HUInt64 handle)
 |     |     |     -> Result
 |     |     |     +-  params :  : // 1
 |     |     |     |      +-  const HUInt64 handle
 ...
 |     |     +-  DataFlowController(const DataFlowController& rhs) = delete
 |     |     |     +-  params :  : // 1
 |     |     |     |      +-  const DataFlowController& rhs
 |     |     +-  DataFlowController(DataFlowController&& rhs) = delete
 |     |     |     +-  params :  : // 1
 |     |     |     |      +-  DataFlowController&& rhs
 |     |     +-  const DataFlowController &operator=(const DataFlowController& rhs) = delete
 |     |     |     -> const DataFlowController
 |     |     |     +-  params :  : // 1
 |     |     |     |      +-  const DataFlowController& rhs
 |     |     +-  const DataFlowController &operator=(DataFlowController&& rhs) = delete
 |     |     |     -> const DataFlowController
 |     |     |     +-  params :  : // 1
 |     |     |     |      +-  DataFlowController&& rhs
 |     +- private method : // 2
 |     |     +-  DataFlowController()
 |     |     +-  ~DataFlowController()
 |     +- private attribute : // 1
 |     |     +-  std::unique_ptr<Impl> m_pImpl
```

&nbsp;

# configuration

'cfg_ca.conf' file has configurations regarding to the CA

* type
  * "cpp" : to execute the CA for C++ code
* extensions
  * specify file extension to check
* rules
  * rules to be executed
* recursive
  * designate if the operation is to be executed recursively or not
* json_output
  * set it true in order to create output file with the JSON formatted result

&nbsp;

## configration file
cfg.conf
```JSON
{
    "type": "cpp",
    "extensions": ["h", "hpp"],
    "rules": [
    	"must::rof", 
    	"must::prohibit_protected", 
    	"must::singleton_getinstance_return", 
    	"must::class_type", 
    	"must::name_suffix", 
    	"must::prohibit_keyword", 
    	"must::prohibit_friend", 
    	"must::prohibit_nested_class",
    	"should::modularity_num_funcs",
    	"should::modularity_num_params",
        "should::prohibit_raw_pointer"
    ],
    "recursive": true,
    "recursive_depth": 2,
    "print_opt": ["print_analysis_table", "print_details"],
    "filter_suffix_name": ["manager"],
    "filter_keyword": ["std::pair", "std::tuple", "::friend"],
    "modular_matrices": {
    	"num_of_public_func": 30,
    	"num_of_params": 7
    },
    "json_output": false,
    "doxygen": {
        "permite_duplicate_param": true
    }
}
```

cfg_cpp.conf
```
{
    "ignore_class_name" : ["Listener", "listener", "Observer", "observer"]
}
```

&nbsp;


# CPP rules

* rof
  * to check if 'Rule of Five' is applied or not
* prohibit_friend
  * to check if friend keyword is used in class
* prohibit_protected
  * to check if protected keyword is used in class
* singleton_getinstance_return
  * to check if getInstance of singleton class returns itself as raw pointer or not
* class_type
  * to check if class type is wrong or not
* prohibit_tuple
  * to check if tuple is used
* prohibit_pair
  * to check if pair is used
* prohibit_nested_class
  * to check if nested class is declared
* modularity_num_funcs
  * number of public methods are limited to 30 or less
* modularity_num_params
  * number of parameters are limited to 7 or less

&nbsp;
